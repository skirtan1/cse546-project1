from flask import Flask, request
from configparser import ConfigParser
import requests
import logging
import uuid

class WebWorker:

    def __init__(self, config) -> None:
        self.app = Flask(__name__)

        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
        self.app.add_url_rule("/", "index", self.index, methods=["GET", "POST"])
        self.app.add_url_rule("/classify", "classify", self.classify, methods=["GET", "POST"])
        self.remote_url = config.get('remote', 'url')

    def index(self):
        return "Hello World"
    
    def classify(self):
        file = request.files
        resp = requests.post(url=self.remote_url, files=file)
        return resp.text
    
    def get_queue(self, name):
        pass
    
    def write_to_msgq(self, messages) -> None:
        pass

    def poll_resp_q(self) -> None:
        pass

if __name__ == "__main__":
    config = ConfigParser()
    config.read('wt_config.ini')

    worker = WebWorker(config=config)
    host=config.get('flask', 'host')
    port=int(config.get('flask', 'port'))
    worker.app.run(host, port)
    
