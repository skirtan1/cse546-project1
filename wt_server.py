from flask import Flask, request
from configparser import ConfigParser
import logging
from utils import *
import boto3
import io
import botocore
import boto3
from uuid import uuid4
import time
import threading
from RWLock import *

resultQueue = dict()
lock = ReadWriteLock()

class WebWorker:

    def __init__(self, config: dict, queue_url: str, sqsClient: boto3.client) -> None:
        """Initialize Web worker

        :param config: parsed config file
        :type config: dict
        :param queue_url: queue url
        :type queue_url: str
        :param sqsClient: sqs client
        :type sqsClient: boto3.client
        """

        #Flask config
        self.app = Flask(__name__)
        self.app.config['SERVER_TIMEOUT'] = 120
        self.app.config['TIMEOUT'] = 120

        # Init logging
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

        # Add url rules and handlers
        self.app.add_url_rule("/", "index", self.index, methods=["GET", "POST"])
        self.app.add_url_rule("/classify", "classify", self.classify, methods=["GET", "POST"])

        # Increase max pool connections, configure boto3
        client_config=botocore.config.Config(
            max_pool_connections=int(config.get('boto', 'max_pool_connections'))
        )

        # create s3 clietn and get input bucket
        self.s3 = boto3.client('s3', config=client_config)
        self.input_bucket = config.get('s3', 'input_bucket')

        # create s3 resource and get queues
        sqs = boto3.resource('sqs')
        self.requestQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','request_queue'))
        self.responseQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','response_queue'))

        self.queue_url = queue_url
        self.sqsClient = sqsClient

    def index(self):
        """Test method to check if server is live"""

        return "Hello World"
    
    def classify(self):
        """classify method used to handler /classify

        :return: result
        :rtype: str
        """

        # Get file from request
        file = request.files.get('myfile')
        mfile = io.BytesIO()
        filename = file.filename
        mfile.write(file.read())

        # Write file to s3 input bucket
        safe_upload(client=self.s3, bucket=self.input_bucket,
                    key=filename, data=mfile, content_type="image/png")
        logging.info("Sending msg to request queue: {}".format(filename))

        # Write the request to request queue
        messageId = self.write_to_msgq(filename)

        # Poll global resultQueue (dict) for resutls
        while True:
            result = getMessageById(messageId, self.queue_url, self.sqsClient)
            if result != 'None':
                break
            time.sleep(1/10)
        return result

    def write_to_msgq(self, message: str) -> str:
        """Try to write message to queue

        :param message: message string
        :type message: str
        :return: messageId if successfull
        :rtype: str
        """
        try:
            response = self.requestQueue.send_message(MessageBody=message)
            logging.info("Got response: {} for msg: {} from request queue".format(response, message))
            return response['MessageId']
        except Exception as e:
            print(f'Error: {str(e)}')

def getMessageById(messageId:str, queue_url:str, sqsClient: boto3.client) -> str:
    """Method to get result from global result queue. Acquires read lock

    :param messageId: messageId string (used as uuid)
    :type messageId: str
    :param queue_url: url of the response queue (to delete message)
    :type queue_url: str
    :param sqsClient: sqs client
    :type sqsClient: boto3.client
    :return: _description_
    :rtype: str
    """
    global resultQueue
    lock.acquire_read()
    ret = 'None'
    if messageId in resultQueue:
        message = resultQueue[messageId]
        sqsClient.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=message['receipt_handle']
        )
        del resultQueue[messageId]
        ret = message['result']
    lock.release_read()
    return ret


def poll_resp_q(queue_url: str, sqsClient: boto3.client) -> str:
    """Poll response queue for results. Acquires write lock, once in a while

    :param queue_url: url of response queue
    :type queue_url: str
    :param sqsClient: sqs client
    :type sqsClient: boto3.client
    :return: If this returns, an exception has been caught
    :rtype: str
    """
    try:
        logging.info("Starting to poll response queue")
        while True:
            response = sqsClient.receive_message(
                QueueUrl=queue_url,
                AttributeNames=[
                    'SentTimestamp'
                ],
                MessageAttributeNames=[
                    'All'
                ],
                VisibilityTimeout=180,
                WaitTimeSeconds=0,
                MaxNumberOfMessages=10,
            )

            if 'Messages' not in response:
                logging.info("Empty Response received from response queue")
                time.sleep(3)
                continue

            global resultQueue

            lock.acquire_write()
            for message in response['Messages']:
                if 'MessageAttributes' in message:
                    messageAttr = message['MessageAttributes']
                    messageId = messageAttr['messageId']['StringValue']
                    resultQueue[messageId] = {
                        'result': message['Body'],
                        'receipt_handle' : message['ReceiptHandle']
                    }
            lock.release_write()
            time.sleep(3)


    except Exception as e: 
        return f'Error: {str(e)}'


if __name__ == "__main__":

    # parse congih
    config = ConfigParser()
    config.read('wt_config.ini')

    # configure boto3
    client_config=botocore.config.Config(
        max_pool_connections=int(config.get('boto', 'max_pool_connections'))
    )

    # get response queue url
    queue_url = config.get('sqs','response_queue_url')

    # sqs client
    sqsClient = boto3.client('sqs', config=client_config)

    # init loggign
    logging.basicConfig(format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=int(config.get('logging', 'level')))
    
    # init WebWorker obj
    worker = WebWorker(config=config, queue_url=queue_url, sqsClient=sqsClient)

    # start polling the response queue
    t = threading.Thread(target=poll_resp_q, args=(queue_url, sqsClient))
    t.start()

    # start flask app
    host=config.get('flask', 'host')
    port=int(config.get('flask', 'port'))
    worker.app.run(host, port)

    # If it's reached here means flask app exited
    # wait for poll thread to join
    t.join()
    
