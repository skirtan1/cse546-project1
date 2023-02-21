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
        self.model = models.resnet18(pretrained=True)
        self.model.eval()

        self.labels = None
        with open(config.get('local', 'labels')) as f:
            self.labels = json.load(f)

        #self.app = Flask(__name__)
        
        #self.app.add_url_rule("/", "index", self.index, methods=["GET","POST"])
        #self.app.add_url_rule("/classify", "classify", self.classify, methods=["GET","POST"])
        # client_config=botocore.config.Config(
        #     max_pool_connections=int(config.get('boto', 'max_pool_connections'))
        # )
        self.s3 = boto3.client('s3')
        self.input_bucket = config.get('s3', 'input_bucket')
        self.output_bucket = config.get('s3', 'output_bucket')

        sqs = boto3.resource('sqs')
        self.requestQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','request_queue'))
        self.responseQueue = sqs.get_queue_by_name(QueueName=config.get('sqs','response_queue'))
        self.count=0

    def index(self):
        return "Hello World"
    
    def classify(self, filename, messageId) -> None:
        #req = request.json
        #filename = req.get('filename')
        logging.info("Classifying image: {}, msgID: {}".format(filename, messageId))
        self.count += 1
        data = safe_download(client=self.s3, bucket=self.input_bucket, key=filename)
        try:
            result = self.evaluate(Image.open(data))
        except Exception as e:
            logging.error("Exception occured: {}, img: {}, msgID: {}".format(e, filename, messageId))
            result = str(e)

        key = filename.split('.')[0]
        result_data = io.BytesIO()
        result_data.write(bytes("({},{})".format(key,result).encode('utf-8')))
        logging.info("Uploading result: {} to s3 bucket: {}".format(result_data, self.output_bucket))
        time.sleep(15)
        safe_upload(client=self.s3, bucket=self.output_bucket,
                    key=key+".txt", data=result_data, content_type="text/plain")
        #response = make_response("({}:{})".format(filename, result), 200)
        #response.mimetype = "text/plain"
        response = "({}:{})".format(filename, result)
        logging.info("Writing {} to response queue".format(response))
        self.write_to_respq(response, messageId)
        logging.info("Serviced {}th request".format(self.count))

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
        except Exception as e:
            print(f'Error: {str(e)}')
    
def poll_msgq(sqsClient, queue_url, worker: AppWorker) -> None:
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
                VisibilityTimeout=30,
                WaitTimeSeconds=0
            )

            if 'Messages' not in response:
                logging.debug("Empty response received from queue")
                time.sleep(10)
                continue

            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']

            messageBody = message['Body']
            messageId = message['MessageId']
            worker.classify(messageBody, messageId)

            sqsClient.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )

        except Exception as e: 
            print(f'Error: {str(e)}')
            time.sleep(10)

if __name__ == "__main__":
    config = ConfigParser()
    config.read('at_config.ini')

    logging.basicConfig(format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=int(config.get('logging', 'level')))

    queue_url = config.get('sqs','request_queue_url')
    sqsClient = boto3.client('sqs')

    worker = AppWorker(config=config)
    #with worker.app.app_context():
    t = Thread(target=poll_msgq, args=(sqsClient, queue_url, worker))
    t.start()

    t.join()
    #worker.app.run(host=config.get("flask", "host"), port=int(config.get("flask", "port")))
    
