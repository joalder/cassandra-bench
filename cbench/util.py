"""
Common utility functions
"""
import boto3

from cbench import settings


def create_instance(name, image=settings.DEFAULT_INSTANCE_IMANGE, type=settings.DEFAULT_INSTANCE_TYPE, start=False):
    ec2 = boto3.resource("ec2")

    user_data = """#cloud-config

    runcmd:
     - apt-get update
     - apt-get install docker docker.io
     - docker pull cassandra:2.2
    """

    instance, = ec2.create_instances(
        ImageId=image,
        KeyName=settings.DEFAULT_KEY_NAME,
        MinCount=1,
        MaxCount=1,
        UserData=user_data,
        InstanceType=type,
        )
    tags = ec2.create_tags(Resources=[instance.id], Tags=[{'Key': "Name", 'Value': name}])

    if start:
        run_cassandra(instance.id)

    return instance


def run_cassandra(instance_id, seeds=list):
    ec2 = boto3.resource("ec2")
    instance = ec2.Instance(instance_id)



def is_reachable(host):
    pass
