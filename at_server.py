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
import time
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

    def index(self):
        return "Hello World"
    
    def classify(self):
        file = request.files
        key = list(file.keys())[0]
        val = file.get(key)
        print(val)
        result = self.evaluate(Image.open(val))
        
        #writing to s3
        self.write_to_s3({key: val})

        #write_to_respq
        self.write_to_respq({key: val})

        response = make_response(result, 200)
        response.mimetype = "text/plain"
        return response

    def evaluate(self, img):
        img_tensor = transforms.ToTensor()(img).unsqueeze_(0)
        outputs = self.model(img_tensor)
        _, predicted = torch.max(outputs.data, 1)
        return self.labels[np.array(predicted)[0]]
    
    def poll_msgq(self) -> None:
    # Write the result to s3
        pass

    def write_to_s3(self, result) -> None:
        pass

    # Write the result to response queue
    def write_to_respq(self, result) -> None:
        pass


if __name__ == "__main__":
    config = ConfigParser()
    config.read('at_config.ini')

    worker = AppWorker(config=config)
    worker.app.run(host=config.get("flask", "host"), port=int(config.get("flask", "port")))
    
