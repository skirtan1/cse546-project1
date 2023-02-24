import datetime
import boto3

QUEUE_NAME = "requests"
ASG_NAME = "App Tier"
REGION_NAME = "us-east-1"

sqs_client = boto3.client('sqs', region_name=REGION_NAME)
asg_client = boto3.client('autoscaling', region_name=REGION_NAME)
cw_client = boto3.client('cloudwatch', region_name=REGION_NAME)

# Get the queue URL
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.get_queue_url
queue_url = sqs_client.get_queue_url(QueueName=QUEUE_NAME).get('QueueUrl', None)
if queue_url is None:
    exit(1)

# Get the size from the queue
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.get_queue_attributes
queue_attributes = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['ApproximateNumberOfMessages'])

number_of_messages = int(queue_attributes['Attributes']['ApproximateNumberOfMessages'])

# Describe autoscaling group
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_auto_scaling_groups
asg_detail = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[ASG_NAME])

# Find the number of `InService` instances in the autoscaling group
asg_instances = asg_detail['AutoScalingGroups'][0]['Instances']
in_service_instances = len([i for i in asg_instances if i['LifecycleState'] == 'InService'])

# Calculate the BacklogPerInstance metric
# 10 is the maximum number of messages allowed to be processed by an EC2
# instance before autoscaling needs to scale out/scale in.
if in_service_instances != 0:
    backlog_per_instance = number_of_messages / in_service_instances
else:
    backlog_per_instance = number_of_messages

# Push the metric to Cloudwatch
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.put_metric_data
cw_client.put_metric_data(
    Namespace='SQSCustomMetric',
    MetricData=[
        {
            'MetricName': 'BacklogPerInstance',
            'Dimensions': [{'Name': 'AutoScaleGroup','Value': ASG_NAME}],
            'Value': backlog_per_instance,
            'Unit': 'None'
        }
    ]
)

print(datetime.datetime.now(), ">", backlog_per_instance)