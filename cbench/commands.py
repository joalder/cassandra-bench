"""
All the commands cbench provides

Preferably do a "from cbench.commands import *" so the state gets initialized properly
"""
import boto3
import plumbum
from plumbum.machines.paramiko_machine import ParamikoMachine
import paramiko
import logging

from cbench import settings
from . import state
from . import util


def create_cluster(num_nodes=3, hosts=list):
    raise Exception("Not implemented yet!")


def create_seed_instance():
    if state.CLUSTER_INSTANCES:
        raise Exception("There already is a cluster!")

    seed_instance = util.create_instance("cassandra-seed-node")

    state.SEED_IP = seed_instance.private_ip_address

    print("Created seed instance with id: {id} and private ip: {ip}".format(id=seed_instance.id,
                                                                            ip=seed_instance.private_ip_address))
    state.CLUSTER_INSTANCES.append(seed_instance.id)

    #TODO: actually start


def add_instance(host, name=None):
    state.CLUSTER_INSTANCES.append(host)


def remove_instance(host, name=None):
    raise Exception("Not implemented yet!")


def add_ycsb_host(host):
    state.YCSB_INSTANCES.append(host)
    raise Exception("Not implemented yet!")


def prepare_benchmark(host, workload):
    raise Exception("Not implemented yet!")


def run_benchmark(host, workload):
    raise Exception("Not implemented yet!")


def list_cluster():
    for instance in state.CLUSTER_INSTANCES:
        print(instance)


def status():
    raise Exception("Not implemented yet!")



