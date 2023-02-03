from flask import Flask, request
from configparser import ConfigParser
import requests

class WebWorker:

    def __init__(self, config) -> None:
        self.app = Flask(__name__)
        self.app.add_url_rule("/", "classify", self.classify, methods=["GET", "POST"])
        self.remote_url = config.get('remote', 'url')

    def classify(self):
        file = request.files
        resp = requests.post(url=self.remote_url, files=file)
        return resp.text

    # Write the result to response queue
    def write_to_msgq(self, val) -> None:
        pass

    def poll_resp_q(self) -> None:
        pass

if __name__ == "__main__":
    config = ConfigParser()
    config.read('wt_config.ini')

    worker = WebWorker(config=config)
    worker.app.run(debug=True)
    
