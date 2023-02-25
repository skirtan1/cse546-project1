import torch
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from PIL import Image
import numpy as np
import json
import io
import time
from utils import *
import boto3
from configparser import ConfigParser
import boto3
from threading import Thread

class AppWorker:

    def __init__(self, config) -> None:
        """Initialize AppWorker object with config

        :param config: Config.ini passed after parsing
        :type config: dict
        """

        # Create the RNN model
        self.model = models.resnet18(pretrained=True)
        self.model.eval()

        # Load labels
        self.labels = None
        with open(config.get('local', 'labels')) as f:
            self.labels = json.load(f)

        # Create s3 client and get buckets
        self.s3 = boto3.client('s3')
        self.input_bucket = config.get('s3', 'input_bucket')
        self.output_bucket = config.get('s3', 'output_bucket')

        # Create sqs resource object and get queues
        sqs = boto3.resource('sqs')
        self.requestQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','request_queue'))
        self.responseQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','response_queue'))
        
        #initialize messages processed to zero
        self.count=0
    
    def classify(self, filename: str, messageId: str) -> None:
        """Classify an image given by the filename and messageId

        :param filename: The filename of the image file
        :type filename: str
        :param messageId: messageId of the message from request queue
        :type messageId: str
        """
        logging.info("Classifying image: {}, msgID: {}".format(filename, messageId))
        self.count += 1

        # Download file from s3 and try to classify
        data = safe_download(client=self.s3, bucket=self.input_bucket, key=filename)
        try:
            result = self.evaluate(Image.open(data))
        except Exception as e:
            logging.error("Exception occured: {}, img: {}, msgID: {}".format(e, filename, messageId))
            result = str(e)

        # Wait to not process very fast
        time.sleep(4.5)


        # upload results to s3
        key = filename.split('.')[0]
        result_data = io.BytesIO()
        result_data.write(bytes("({},{})".format(key,result).encode('utf-8')))
        logging.info("Uploading result: {} to s3 bucket: {}".format(result_data, self.output_bucket))
        safe_upload(client=self.s3, bucket=self.output_bucket,
                    key=key+".txt", data=result_data, content_type="text/plain")
        
        response = "({}:{})".format(filename, result)
        logging.info("Writing {} to response queue".format(response))

        # write response to response queue
        self.write_to_respq(response, messageId)
        logging.info("Serviced {}th request".format(self.count))

    def evaluate(self, img: io.BytesIO) -> str:
        """Given byte file img classify it using the model

        :param img: byte file
        :type img: io.BytesIO
        :return: The label which was predicted as the image
        :rtype: str
        """
        img_tensor = transforms.ToTensor()(img).unsqueeze_(0)
        outputs = self.model(img_tensor)
        _, predicted = torch.max(outputs.data, 1)
        return self.labels[np.array(predicted)[0]]

    def write_to_respq(self, result: str, messageId: str) -> None:
        """Write response str and messageId to response queue

        :param result: result string
        :type result: str
        :param messageId: messageId given by request queue
        :type messageId: str
        """
        try:
            self.responseQueue.send_message(
                MessageBody=result,
                MessageAttributes={
                    'messageId':{
                        'DataType':'String',
                        'StringValue': messageId
                    } 
                }
            )
        except Exception as e:
            print(f'Error: {str(e)}')

# Function to poll queues
def poll_msgq(sqsClient: boto3.client, queue_url: str, worker: AppWorker) -> None:
    """Poll the request queue for any available message to be processed

    :param sqsClient: sqs client
    :type sqsClient: boto3.client
    :param queue_url: url of the queue to poll
    :type queue_url: str
    :param worker: App worker created
    :type worker: AppWorker
    """
    while True:
        try:

            # receive message from request queue
            response = sqsClient.receive_message(
                QueueUrl=queue_url,
                AttributeNames=[
                    'SentTimestamp'
                ],
                MaxNumberOfMessages=1,
                MessageAttributeNames=[
                    'All'
                ],
                VisibilityTimeout=30,
                WaitTimeSeconds=0
            )

            # Empty response
            if 'Messages' not in response:
                logging.debug("Empty response received from queue")
                time.sleep(10)
                continue
            
            # Get file name
            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']

            # Get  messageId
            messageBody = message['Body']
            messageId = message['MessageId']

            # classify and write response to s3, sqs
            worker.classify(messageBody, messageId)

            # delete message from request queue
            sqsClient.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )

        except Exception as e: 
            print(f'Error: {str(e)}')
            time.sleep(10)

if __name__ == "__main__":

    # parse the config file
    config = ConfigParser()
    config.read('at_config.ini')

    # initialize logger
    logging.basicConfig(format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=int(config.get('logging', 'level')))


    # creatae sqs client
    queue_url = config.get('sqs','request_queue_url')
    sqsClient = boto3.client('sqs')

    # initialize worker obj
    worker = AppWorker(config=config)

    # start poll thread
    t = Thread(target=poll_msgq, args=(sqsClient, queue_url, worker))
    t.start()

    # wait for polling to terminate (or possibly not)
    t.join()
    
