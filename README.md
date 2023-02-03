# cse546-project1
cloud computing project 1

use with workload generator:
```
 python3 multithread_workload_generator.py \
--num_request 10 \
--url 'http://localhost:5000' \
--image_folder "./imagenet-100/"
```

generator here: https://github.com/nehavadnere/CSE546_Sum22_workload_generator

Tasks:
[] Implement code to push to sqs
[] Implement code to poll from sqs
[] Implement code to write to s3
