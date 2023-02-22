from flask import Flask, request
from configparser import ConfigParser
import requests
import logging
import uuid
from utils import *
import boto3
import io
import botocore
import boto3
import base64
from uuid import uuid4
import concurrent.futures
import time
import threading

resultQueue = dict()
writeLock = threading.Lock()

class WebWorker:

    def __init__(self, config, queue_url, sqsClient) -> None:
        self.app = Flask(__name__)
        self.app.config['SERVER_TIMEOUT'] = 120
        self.app.config['TIMEOUT'] = 120

        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
        self.app.add_url_rule("/", "index", self.index, methods=["GET", "POST"])
        self.app.add_url_rule("/classify", "classify", self.classify, methods=["GET", "POST"])
        self.remote_url = config.get('remote', 'url')
        client_config=botocore.config.Config(
            max_pool_connections=int(config.get('boto', 'max_pool_connections'))
        )
        self.s3 = boto3.client('s3', config=client_config)
        self.input_bucket = config.get('s3', 'input_bucket')

        sqs = boto3.resource('sqs')
        self.requestQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','request_queue'))
        self.responseQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','response_queue'))

        self.queue_url = queue_url
        self.sqsClient = sqsClient

    def index(self):
        return "Hello World"
    
    def classify(self):
        file = request.files.get('myfile')
        mfile = io.BytesIO()
        filename = file.filename
        mfile.write(file.read())
        safe_upload(client=self.s3, bucket=self.input_bucket,
                    key=filename, data=mfile, content_type="image/png")
        logging.info("Sending msg to request queue: {}".format(filename))
        messageId = self.write_to_msgq(filename)
        while True:
            result = getMessageById(messageId, self.queue_url, self.sqsClient)
            if result != 'None':
                break
            time.sleep(2) #timeout for debugging
        return result

    def write_to_msgq(self, message) -> str:
        try:
            response = self.requestQueue.send_message(MessageBody=message)
            logging.info("Got response: {} for msg: {} from request queue".format(response, message))
            return response['MessageId']
        except Exception as e:
            print(f'Error: {str(e)}')

def getMessageById(messageId:str, queue_url, sqsClient) -> str:
    global resultQueue
    with writeLock:
        if messageId in resultQueue:
            message = resultQueue[messageId]
            sqsClient.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message['receipt_handle']
            )
            del resultQueue[messageId]
        else:
            return 'None'
    return message['result']


def poll_resp_q(queue_url: str, sqsClient) -> str:
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
                WaitTimeSeconds=0
            )

            if 'Messages' not in response:
                logging.info("Empty Response received from response queue")
                time.sleep(3)
                continue

            global resultQueue

            for message in response['Messages']:
                if 'MessageAttributes' in message:
                    messageAttr = message['MessageAttributes']
                    messageId = messageAttr['messageId']['StringValue']
                    with writeLock:
                        resultQueue[messageId] = {
                            'result': message['Body'],
                            'receipt_handle' : message['ReceiptHandle']
                        }
            time.sleep(3)


    except Exception as e: 
        return f'Error: {str(e)}'


if __name__ == "__main__":
    config = ConfigParser()
    config.read('wt_config.ini')

    client_config=botocore.config.Config(
        max_pool_connections=int(config.get('boto', 'max_pool_connections'))
    )
    queue_url = config.get('sqs','response_queue_url')
    sqsClient = boto3.client('sqs', config=client_config)

    logging.basicConfig(format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=int(config.get('logging', 'level')))
    worker = WebWorker(config=config, queue_url=queue_url, sqsClient=sqsClient)

    t = threading.Thread(target=poll_resp_q, args=(queue_url, sqsClient))
    t.start()

    host=config.get('flask', 'host')
    port=int(config.get('flask', 'port'))
    worker.app.run(host, port)
    
