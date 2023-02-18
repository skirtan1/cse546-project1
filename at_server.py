import os
from flask import Flask, request, make_response
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

class AppWorker:

    def __init__(self, config) -> None:
        self.model = models.resnet18(pretrained=True)
        self.model.eval()

        self.labels = None
        with open(config.get('local', 'labels')) as f:
            self.labels = json.load(f)



        self.app = Flask(__name__)
        self.app.add_url_rule("/", "index", self.index, methods=["GET","POST"])
        self.app.add_url_rule("/classify", "classify", self.classify, methods=["GET","POST"])
        client_config=botocore.config.Config(
            max_pool_connections=int(config.get('boto', 'max_pool_connections'))
        )
        self.s3 = boto3.client('s3', config=client_config)
        self.input_bucket = config.get('s3', 'input_bucket')
        self.output_bucket = config.get('s3', 'output_bucket')

    def index(self):
        return "Hello World"
    
    def classify(self):
        req = request.json
        filename = req.get('filename')
        
        data = safe_download(client=self.s3, bucket=self.input_bucket, key=filename)
        result = self.evaluate(Image.open(data))

        key = filename.split('.')[0]
        result_data = io.BytesIO()
        result_data.write(bytes("({},{})".format(key,result).encode('utf-8')))
        safe_upload(client=self.s3, bucket=self.output_bucket,
                    key=key+".txt", data=result_data, content_type="text/plain")
        response = make_response("({}:{})".format(filename, result), 200)
        response.mimetype = "text/plain"
        return response

    def evaluate(self, img):
        img_tensor = transforms.ToTensor()(img).unsqueeze_(0)
        outputs = self.model(img_tensor)
        _, predicted = torch.max(outputs.data, 1)
        return self.labels[np.array(predicted)[0]]


if __name__ == "__main__":
    config = ConfigParser()
    config.read('at_config.ini')

    worker = AppWorker(config=config)
    worker.app.run(host=config.get("flask", "host"), port=int(config.get("flask", "port")))
    
