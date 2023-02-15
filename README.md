# cse546-project1
cloud computing project 1

To test with dockerfiles:

1. Make at_server (3.0 GB image):
```
make at_server
```
2. Make wt_server (700 MB image):
```
make wt_server
```
3. run at_server
```
docker run --name at_server -p 8000:8000 at_server:latest
```
4. run wt_server
```
docker run --name wt_server --link at_server -p 5000:5000 wt_server:latest
```
5. use workload generator

use with workload generator:
```
 python3 multithread_workload_generator.py \
--num_request 10 \
--url 'http://localhost:5000/classify' \
--image_folder "./imagenet-100/"
```

generator here: https://github.com/nehavadnere/CSE546_Sum22_workload_generator

Tasks:
- [ ] Implement code to push to sqs
- [ ] Implement code to poll from sqs
- [ ] Implement code to write to s3
