"""
All the commands cbench provides

Preferably do a "from cbench.commands import *" so the state gets initialized properly
"""
import os
from datetime import datetime
from time import sleep
import logging
from shutil import copy2

import boto3

from cbench import settings
from . import state
from . import util
from . import graph

log = logging.getLogger('')
action_log = logging.getLogger('cbench.actions')

ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')


@util.action
def create_cluster(hosts):
    if not state.SEED_IP:
        state.SEED_IP = ec2.Instance(hosts[0]).private_ip_address
    for host in hosts:
        util.run_cassandra(host)


@util.action
def create_instances(num=2, group=None, setup='cassandra', type=settings.DEFAULT_INSTANCE_TYPE):
    instances = []
    for i in range(num):
        name = "{0}-{1}".format(setup, len(group) + i)
        instance = util.create_instance(name, setup=setup, type=type)
        log.info("Created instance with id: {id} private ip: {ip} public ip: {pip}".format(
            id=instance.id,
            ip=instance.private_ip_address,
            pip=instance.public_ip_address))
        instances.append(instance)

    if isinstance(group, list):
        group.extend([i.id for i in instances])

    return instances


@util.action
def remove_cassandra_instance(instance_id):
    # util.docker_exec(state.CLUSTER_INSTANCES[0], ["nodetool", "ring"])
    util.docker_exec(state.CLUSTER_INSTANCES[0], ["nodetool", "status"])
    util.decommission_cassandra(instance_id)
    util.docker_exec(state.CLUSTER_INSTANCES[0], ["nodetool", "ring"])
    util.docker_exec(state.CLUSTER_INSTANCES[0], ["nodetool", "status"])


@util.action
def scale_cluster(instances):
    # util.docker_exec(state.CLUSTER_INSTANCES[0], ["nodetool", "ring"])
    util.docker_exec(state.CLUSTER_INSTANCES[0], ["nodetool", "status"])
    for instance_id in instances:
        if util.is_cassandra_running(instance_id):
            msg = "Detected already running instance on {0}".format(instance_id)
            log.error(msg)
            raise Exception(msg)
        util.run_cassandra(instance_id)
    util.docker_exec(state.CLUSTER_INSTANCES[0], ["nodetool", "ring"])
    util.docker_exec(state.CLUSTER_INSTANCES[0], ["nodetool", "status"])


@util.action
def prepare_benchmark(workload="workloads/workload_read", name=None, description=None, add_args=list()):
    if not (state.YCSB_INSTANCES and state.CLUSTER_INSTANCES):
        raise Exception("Cluster (and YCSB host) not yet initialized properly!")

    state.RUN_NAME = name if name else datetime.now().strftime('%Y%m%d%H%m%S')
    state.RUN_DESCRIPTION = description
    state.WORKLOAD = workload

    log.info("Creating keyspace YCSB and table..")
    # Create keyspace and table
    with util.Fragile(util.connect(state.CLUSTER_INSTANCES[0])) as seed_instance:
        sudo = seed_instance["sudo"]
        ret = sudo["docker", "exec", "cassy", "cqlsh", "-e", """DESCRIBE KEYSPACES"""]()
        if "ycsb" in ret:
            log.info("Keyspace seems to exists already!!")
            raise util.Fragile.Break
        ret = sudo["docker", "exec", "cassy", "cqlsh", "-e",
                     """create keyspace ycsb WITH REPLICATION = {'class' : 'SimpleStrategy', 'replication_factor': 3 };
                    USE ycsb;
                    create table usertable (
                        y_id varchar primary key,
                        field0 varchar,
                        field1 varchar,
                        field2 varchar,
                        field3 varchar,
                        field4 varchar,
                        field5 varchar,
                        field6 varchar,
                        field7 varchar,
                        field8 varchar,
                        field9 varchar);"""]()
        log.info("Result: " + ret)

    # Load data with ycsb
    log.info("Loading YCSB data for workload '{0}'".format(workload))
    with util.connect(state.YCSB_INSTANCES[0]) as ycsb_instance:
        with ycsb_instance.cwd("/home/ubuntu/ycsb"):
            ycsb = ycsb_instance["bin/ycsb"]
            ret = ycsb("load", "cassandra2-cql", "-threads", "40", "-P", "workloads/workload_base", "-P", workload, "-p", "hosts=" + ",".join(util.cluster_ips()), *add_args)
            log.info("Result: " + ret)


@util.action
def start_benchmark(threads=1, add_args=list()):
    if not (state.RUN_NAME and state.WORKLOAD):
        raise Exception("Benchmark not setup properly! Use prepare_benchmark() first!")

    log.info("Starting run '{0}' with workload '{1}'".format(state.RUN_NAME, state.WORKLOAD))
    # Todo: Run on all YCSB instances
    with util.connect(state.YCSB_INSTANCES[0]) as ycsb_instance:
        with ycsb_instance.cwd("/home/ubuntu/ycsb"):
            cmd = ycsb_instance["bin/ycsb"]
            ret = cmd("run", "cassandra2-cql", "-s", "-threads", threads, "-l", state.RUN_NAME,
                      "-P", "workloads/workload_base", "-P", state.WORKLOAD,
                      "-p", "hosts=" + ",".join(util.cluster_ips()), *add_args, ">", "ycsb.log", "2>&1")
            log.info("Result: " + ret)


@util.action
def wait_for_finish():
    while not util.is_benchmark_done():
        sleep(10)
    log.info("No more YCSB running!")


@util.action
def gather_results():
    result_dir = os.path.abspath(os.path.join(settings.RESULT_DIR, state.RUN_NAME))
    if not os.path.isdir(result_dir):
        os.makedirs(result_dir)

    log.info("Gathering results into '{0}'".format(result_dir))

    for i, instance in enumerate(state.YCSB_INSTANCES):
        with util.connect(instance) as remote:
            remote.download("~/ycsb/ycsb.log", os.path.join(result_dir, "ycsb_{0}.log".format(i)))

    with open(os.path.join(result_dir, "cbench.state"), "w") as fh:
        for var in dir(state):
            if var.startswith("_"):
                continue
            fh.write("{var}={value}\n".format(var=var, value=repr(getattr(state, var))))

    with open(os.path.join(result_dir, "cbench.settings"), "w") as fh:
        for var in dir(settings):
            if var.startswith("_"):
                continue
            fh.write("{var}={value}\n".format(var=var, value=repr(getattr(settings, var))))

    for logger in [log, action_log]:
        for handler in logger.handlers:
            handler.flush()

    copy2(settings.LOGGING['handlers']['file_general']['filename'], result_dir)
    copy2(settings.LOGGING['handlers']['file_action']['filename'], result_dir)

    for i, instance in enumerate(state.CLUSTER_INSTANCES):
        log.info("Connecting to instance {nr} {name} for results".format(nr=i, name=instance))
        with util.connect(instance) as remote:
            sudo = remote["sudo"]
            try:
                result = sudo("docker", "logs", "cassy", ">cassy.log", "2>&1")
                remote.download("cassy.log", os.path.join(result_dir, "cassandra_{0}.log".format(i)))
                #with open(os.path.join(result_dir, "cassandra_{0}.log".format(i)), 'w') as fh:
                #    fh.write(result)
            except Exception as e:
                log.warning("Could not gather info from {0}! Error: {1}".format(instance, e))


def cleanup_logs():
    for logfile in [settings.LOGGING['handlers']['file_general']['filename'],
                    settings.LOGGING['handlers']['file_action']['filename']]:
        with open(logfile, "wb") as fh:
            fh.truncate()


@util.action
def terminate_instance(id):
    log.warning("Going to terminate instance '{0}'".format(id))
    ec2.Instance(id).terminate()


def terminate_cluster():
    for id in state.CLUSTER_INSTANCES:
        terminate_instance(id)


def terminate_all():
    terminate_cluster()
    for id in state.YCSB_INSTANCES:
        terminate_instance(id)


def list_instances():
    for reservation in ec2_client.describe_instances()['Reservations']:
        for instance in reservation['Instances']:
            tags = "[{0}]".format(", ".join(tag['Key'] + ": " + tag['Value'] for tag in instance['Tags']))
            log.info("ID: {id}, State: {state}, Type: {type}, IP: {ip}, PubIP: {pub_ip}, Tags: {tags}".format(
                id=instance['InstanceId'],
                state=instance['State']['Name'],
                type=instance['InstanceType'],
                ip=instance.get('PrivateIpAddress', '0.0.0.0'),
                pub_ip=instance.get('PublicIpAddress', '0.0.0.0'),
                tags=tags,
            ))


@util.action
def load_state():
    for reservation in ec2_client.describe_instances(
            Filters=[{'Name': 'tag-value', 'Values': ['cassandra-*']},
                     {'Name': 'instance-state-name', 'Values': ['pending', 'running']}])['Reservations']:
        for instance in reservation['Instances']:
            if instance['InstanceId'] not in state.CLUSTER_INSTANCES:
                state.CLUSTER_INSTANCES.append(instance['InstanceId'])

    if state.CLUSTER_INSTANCES:
        state.SEED_IP = ec2.Instance(state.CLUSTER_INSTANCES[0]).private_ip_address

    for reservation in ec2_client.describe_instances(
            Filters=[{'Name': 'tag-value', 'Values': ['ycsb-*']},
                     {'Name': 'instance-state-name', 'Values': ['pending', 'running']}])['Reservations']:
        for instance in reservation['Instances']:
            if instance['InstanceId'] not in state.YCSB_INSTANCES:
                state.YCSB_INSTANCES.append(instance['InstanceId'])


def plot(run_name=None, measurements=None, op_types=None, granularity=30):
    if not run_name:
        run_name = state.RUN_NAME
    graph.plot(run_name, granularity=granularity)

def status():
    raise Exception("Not implemented yet!")
