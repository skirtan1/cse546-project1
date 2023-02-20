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

class WebWorker:

    def __init__(self, config) -> None:
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

        self.queue_url = config.get('sqs','response_queue_url')
        self.sqsClient = boto3.client('sqs')

    def index(self):
        return "Hello World"
    
    def classify(self):
        file = request.files.get('myfile')
        mfile = io.BytesIO()
        filename = file.filename
        print(f'got classify request for {filename}')
        mfile.write(file.read())
        safe_upload(client=self.s3, bucket=self.input_bucket,
                    key=filename, data=mfile, content_type="image/png")
        #resp = requests.post(url=self.remote_url, json={
        #    "filename": filename,
        #    "Key": 1
        #})
        messageId = self.write_to_msgq(filename)
        print(f'messageid: {messageId}')
        with concurrent.futures.ThreadPoolExecutor() as executor:
            print('start polling resp queue for result')
            future = executor.submit(poll_resp_q, messageId, self.queue_url, self.sqsClient)
            result = future.result()
            print(result)
        return result

    def write_to_msgq(self, message) -> str:
        try:
            response = self.requestQueue.send_message(MessageBody=message)
            print(f'wrote message: {message} to request queue')
            return response['MessageId']
        except Exception as e:
            print(f'Error: {str(e)}')

def poll_resp_q(messageId:str, queue_url: str, sqsClient) -> str:
    print('bruhh')
    print(queue_url)
    print(messageId)
    try:
        while True:
            response = sqsClient.receive_message(
                QueueUrl=queue_url,
                AttributeNames=[
                    'SentTimestamp'
                ],
                MessageAttributeNames=[
                    'All'
                ],
                VisibilityTimeout=0,
                WaitTimeSeconds=0
            )
            print(response)

            if 'Messages' not in response:
                print('no messages found in resp queue')
                time.sleep(10)
                continue

            for message in response['Messages']:
                if 'MessageAttributes' in message:
                    messageAttr = message['MessageAttributes']
                    if messageAttr['messageId']['StringValue'] == messageId:
                        print('message found')
                        receipt_handle = message['ReceiptHandle']
                        result = message['Body']
                        sqsClient.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=receipt_handle
                        )
                        return result
            time.sleep(10)


    except Exception as e: 
        return f'Error: {str(e)}'


if __name__ == "__main__":
    config = ConfigParser()
    config.read('wt_config.ini')

    worker = WebWorker(config=config)
    host=config.get('flask', 'host')
    port=int(config.get('flask', 'port'))
    worker.app.run(host, port)
    
