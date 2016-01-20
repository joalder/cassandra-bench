"""
Common utility functions
"""
from time import sleep
import logging

import boto3
import paramiko
from plumbum import SshMachine
from plumbum.machines.paramiko_machine import ParamikoMachine
from plumbum.commands import base

from . import state
from . import settings

log = logging.getLogger('')
action_log = logging.getLogger('cbench.actions')

ec2 = boto3.resource("ec2")

# Hack to use background commands through paramiko
base._safechars += ">&"


def create_instance(name, image=settings.DEFAULT_INSTANCE_IMANGE, type=settings.DEFAULT_INSTANCE_TYPE, setup='cassandra'):

    instance, = ec2.create_instances(
        ImageId=image,
        KeyName=settings.DEFAULT_KEY_NAME,
        MinCount=1,
        MaxCount=1,
        UserData=settings.SETUPS[setup],
        InstanceType=type,
        )
    tags = ec2.create_tags(Resources=[instance.id], Tags=[{'Key': "Name", 'Value': name}])

    # log.info("Waiting for startup of {id}..".format(id=instance.id))
    # instance.wait_until_running()
    # log.info("Go for Green! State: {state}".format(state=instance.state))

    return instance


def run_cassandra(instance_id):
    instance = ec2.Instance(instance_id)

    # Check the seed, don't give it to instance if she is the seed
    seed_ip = state.SEED_IP if instance.private_ip_address != state.SEED_IP else ""

    log.info("Checking instance '{id}' state: {state}".format(id=instance_id, state=instance.state))

    log.info("Connecting to {ip}".format(ip=instance.public_ip_address))
    with connect(instance_id) as remote:
        cmd = remote["sudo"]
        ret = cmd["docker", "run", "-d", "--name", "cassy", "-e", "CASSANDRA_SEEDS=" + seed_ip, "--net", "host", "cassandra:2.2"]()

    #After starting the seed instance we wait a little, to let it startup (seed) or bootstrap (others)
    sleep_time = 60 if seed_ip else 5
    log.info("Going to wait for {0} seconds for startup or bootstrap to finish".format(sleep_time))
    sleep(sleep_time)

    log.info("Command returned:")
    log.info(ret)

    docker_status(instance_id)


def decommission_cassandra(instance_id):
    if not is_cassandra_running(instance_id):
        log.error("No docker container running on instance '{0}'".format(instance_id))
        return

    ret = docker_exec(instance_id, ["nodetool", "decommission"])

    log.info("Nodetool decomissioning returned: {0}".format(ret))


def is_cassandra_running(instance_id):
    if "cassy" in docker_status(instance_id):
        return True
    return False


def docker_status(instance_id):
    with connect(instance_id) as remote:
        cmd = remote["sudo"]
        status = cmd["docker", "ps"]()

        log.info("Docker containers status:")
        log.info(status)
    return status


def docker_exec(instance_id, command):
    with connect(instance_id) as remote:
        cmd = remote["sudo"]
        ret = cmd("docker", "exec", "cassy", *command)
        log.info("docker exec {0} on {1} returned:".format(command, instance_id))
        log.info(ret)
        return ret


def connect(instance_id):
    instance = ec2.Instance(instance_id)
    return ParamikoMachine(instance.public_ip_address, user="ubuntu", keyfile=settings.KEY_FILE, missing_host_policy=paramiko.AutoAddPolicy())


def cluster_ips(type="private", last=False):
    ips = []
    for id in state.CLUSTER_INSTANCES:
        if type == "private":
            ip = ec2.Instance(id).private_ip_address
        else:
            ip = ec2.Instance(id).public_ip_address
        if ip:
            ips.append(ip)
    return ips if last else ips[:-1]


def is_benchmark_done():
    done = True
    for instance in state.YCSB_INSTANCES:
        with connect(instance) as remote:
            ps = remote["ps"]
            ret = ps["-fu", "ubuntu"]()
            if "ycsb" in ret:
                done = False
    return done


def is_reachable(host):
    pass


def action(function):
    """
    Decorator for function wrapping and logging of calls with arguments
    :param function: function to log
    :return: the decorator wrapper
    """
    def _wrapper(*args, **kwargs):
        global action_log

        action_log.info("Run {run} start of '{function}' args: {args} kwargs: {kwargs}".format(
            run=state.RUN_NAME,
            function=function.__name__,
            args=args,
            kwargs=kwargs))
        ret = function(*args, **kwargs)
        action_log.info("Run {run} end of '{function}'".format(run=state.RUN_NAME, function=function.__name__))

    return _wrapper


class Fragile(object):
    class Break(Exception):
      """Break out of the with statement"""

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value.__enter__()

    def __exit__(self, etype, value, traceback):
        error = self.value.__exit__(etype, value, traceback)
        if etype == self.Break:
            return True
        return error


class LevelFilter(logging.Filter):
    def __init__(self, levels=list()):
        self.levels = levels
        super(LevelFilter, self).__init__()

    def filter(self, record):
        if record.levelno not in self.levels:
            return False
        return True
