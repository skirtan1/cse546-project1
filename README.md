# cse546-project1

## Cloud Computing Project 1

### Group: CCP

#### Team Members

| Name  | ASU ID  |
|---|---|
| Gaurav Kulkarni  |  1225477253 |
| Parth Shah | 1225457038 |
| Shreyas Kirtane | 1225453736 |

-----

> [Project Report](https://docs.google.com/document/d/1eQ5AvgC0n3BekTS4ZtOBorB4yhmfZ7G9/edit?usp=sharing&ouid=107186202899619445000&rtpof=true&sd=true)

-----

##### Gaurav's Tasks:

- [x] Researched about Amazon Cloudwatch metrics and alarm, Autoscaling groups and scaling policies
- [x] Tested out different simple step and target tracking policies along with custom metrics
- [x] Evaluated individual policies against the required time limit and scaling requirements
- [x] Managed the documentation of the project

##### Parth's Tasks:

- [x] Implement SQS method in web tier to push messages to request queue
- [x] Implement SQS method in app tier to push results to response queue
- [x] Add multithreading to app tier and web tier to poll SQS queues in background

-----

##### Shreyas's Tasks:

- [x] Implement Web Tier using Flask
- [x] Incorporate image classification in app tier server
- [x] Implement multiple reader single writer lock to poll result dict efficiently
- [x] Implement S3 methods to download and upload files
- [x] Create dockerfile, Makefile, configs, venv requirements file
- [x] Figure out deployment

-----

#### AWS Credentials

* user: demo
* password: eKwG9(sU-ZoWpE/\T"i"
* aws_access_key_id: AKIAYPYDTGY4UM3UQCOJ
* aws_secret_access_key: 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
* default region: us-east-1
* sign-in URL: https://583586231865.signin.aws.amazon.com/console

-----

#### PEM keys

* app tier (all instances): cse546-project1/app-tier-key.pem
* web iter: cse546-project1/web-tier-key.pem

Usage:
```
chmod 600 web-tier-key.pem
ssh -i web-tier-key.pem ec2-user@[public-ip]
```

-----

#### Web Tier details

* Base AMI: AWS-Linux
* user: ec2-user
* ssh-key: cse546-project1/web-tier-key.pem
* public-ip: assigned when started/launced (see ec2 console)

-----

#### SQS

* request queue: requests
* request queue url: https://sqs.us-east-1.amazonaws.com/583586231865/requests

* response queue: responses
* response queue url: https://sqs.us-east-1.amazonaws.com/583586231865/responses

-----

#### S3

* input bucket: cse546images
* resuls bucket: cse546results

------

#### Deploy on your aws account

1. Create queues and buckets
2. Create an ec2 instance name "web-instance" and install docker on it.
3. Configure aws credentials using aws configure or env variables
4. Clone the git repo and do:
    ```
    make run_wt
    ```
4. Create an ec2 instance named "app-instance" and install docker.
5. Configure aws credentials using aws configure or env variables
6. Clone the git repo and do:
    ```
    make run_at
    ```
7. Create an AMI out of app-instance.
8. Create a launch template using this AMI
9. Create an Alarm based on ApproximateNumberOfVissibleMessages on request queue
10. Create an AutoScalingGroup with a step policy
11. Create steps:
    * set 1 capacity for metric >= 1 and < 2.
    * set 2 capacity for metric >= 2 and < 3.
    * ...
    * ...
    * set 20 capacity for metric >= 20 and < +ve infinity
13. Create a simple scale in policy to scale in:
    configure to remove 20 instances when alarm in OK state
14. Attach alarm to the scaling policy
15. Run the workload generator on public ip of web instance
