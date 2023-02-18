from flask import Flask, request
from configparser import ConfigParser
import requests
import logging
import uuid
from utils import *
import boto3
import io
import botocore

class WebWorker:

    def __init__(self, config) -> None:
        self.app = Flask(__name__)

        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
        self.app.add_url_rule("/", "index", self.index, methods=["GET", "POST"])
        self.app.add_url_rule("/classify", "classify", self.classify, methods=["GET", "POST"])
        self.remote_url = config.get('remote', 'url')
        client_config=botocore.config.Config(
            max_pool_connections=int(config.get('boto', 'max_pool_connections'))
        )
        self.s3 = boto3.client('s3', config=client_config)
        self.input_bucket = config.get('s3', 'input_bucket')

    def index(self):
        return "Hello World"
    
    def classify(self):
        file = request.files.get('myfile')
        mfile = io.BytesIO()
        filename = file.filename
        mfile.write(file.read())
        safe_upload(client=self.s3, bucket=self.input_bucket,
                    key=filename, data=mfile, content_type="image/png")
        resp = requests.post(url=self.remote_url, json={
            "filename": filename,
            "Key": 1
        })
        return resp.text

if __name__ == "__main__":
    config = ConfigParser()
    config.read('wt_config.ini')

    worker = WebWorker(config=config)
    host=config.get('flask', 'host')
    port=int(config.get('flask', 'port'))
    worker.app.run(host, port)
    
