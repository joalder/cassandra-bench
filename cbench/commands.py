"""
All the commands cbench provides

Preferably do a "from cbench.commands import *" so the state gets initialized properly
"""

import plumbum
from plumbum.machines.paramiko_machine import ParamikoMachine
import paramiko

from . import state


def create_cluster(num_nodes=3, hosts=[]):
    raise Exception("Not implemented yet!")


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



