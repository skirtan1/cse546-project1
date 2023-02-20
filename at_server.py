import os
#from flask import Flask, request, make_response
import torch
import torchvision
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from PIL import Image
import numpy as np
import json
import sys
import io
import time
from utils import *
import boto3
import botocore
from configparser import ConfigParser
import boto3
from threading import Thread

class AppWorker:

    def __init__(self, config) -> None:
        self.model = models.resnet18(pretrained=True)
        self.model.eval()

        self.labels = None
        with open(config.get('local', 'labels')) as f:
            self.labels = json.load(f)

        #self.app = Flask(__name__)
        
        #self.app.add_url_rule("/", "index", self.index, methods=["GET","POST"])
        #self.app.add_url_rule("/classify", "classify", self.classify, methods=["GET","POST"])
        client_config=botocore.config.Config(
            max_pool_connections=int(config.get('boto', 'max_pool_connections'))
        )
        self.s3 = boto3.client('s3', config=client_config)
        self.input_bucket = config.get('s3', 'input_bucket')
        self.output_bucket = config.get('s3', 'output_bucket')

        sqs = boto3.resource('sqs')
        self.requestQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','request_queue'))
        self.responseQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','response_queue'))

    def index(self):
        return "Hello World"
    
    def classify(self, filename, messageId) -> None:
        #req = request.json
        #filename = req.get('filename')
        print('classify function called') 
        data = safe_download(client=self.s3, bucket=self.input_bucket, key=filename)
        try:
            result = self.evaluate(Image.open(data))
        except Exception as e:
            result = str(e)

        key = filename.split('.')[0]
        result_data = io.BytesIO()
        result_data.write(bytes("({},{})".format(key,result).encode('utf-8')))
        safe_upload(client=self.s3, bucket=self.output_bucket,
                    key=key+".txt", data=result_data, content_type="text/plain")
        #response = make_response("({}:{})".format(filename, result), 200)
        #response.mimetype = "text/plain"
        response = "({}:{})".format(filename, result)
        self.write_to_respq(response, messageId)

    def evaluate(self, img):
        img_tensor = transforms.ToTensor()(img).unsqueeze_(0)
        outputs = self.model(img_tensor)
        _, predicted = torch.max(outputs.data, 1)
        return self.labels[np.array(predicted)[0]]

    def write_to_respq(self, result, messageId) -> None:
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
            print(f'wrote message: {result} to response queue')
        except Exception as e:
            print(f'Error: {str(e)}')
    
def poll_msgq(sqsClient, queue_url, worker: AppWorker) -> None:
    print('start polling')
    while True:
        try:
            response = sqsClient.receive_message(
                QueueUrl=queue_url,
                AttributeNames=[
                    'SentTimestamp'
                ],
                MaxNumberOfMessages=1,
                MessageAttributeNames=[
                    'All'
                ],
                VisibilityTimeout=60,
                WaitTimeSeconds=0
            )

            if 'Messages' not in response:
                print('no messages found in req queue')
                time.sleep(10)
                continue

            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']

            sqsClient.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )

            print('Received and deleted message: %s' % message)
            messageBody = message['Body']
            messageId = message['MessageId']
            print(f'messageid: {messageId}')
            worker.classify(messageBody, messageId)

        except Exception as e: 
            print(f'Error: {str(e)}')
            time.sleep(10)

if __name__ == "__main__":
    config = ConfigParser()
    config.read('at_config.ini')

    queue_url = config.get('sqs','request_queue_url')
    sqsClient = boto3.client('sqs')

    worker = AppWorker(config=config)
    #with worker.app.app_context():
    t = Thread(target=poll_msgq, args=(sqsClient, queue_url, worker))
    t.start()
    #worker.app.run(host=config.get("flask", "host"), port=int(config.get("flask", "port")))
    
