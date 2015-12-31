import logging

DEFAULT_INSTANCE_TYPE = "t2.medium"
DEFAULT_INSTANCE_IMANGE = "ami-accff2b1"
DEFAULT_KEY_NAME = "jtech_key"

KEY_FILE = "C:\\Users\\Jonas\\.ssh\\jtech_key"

RESULT_DIR = "results"

SETUPS = {
    'cassandra': """#cloud-config

    packages:
     - docker
     - docker.io
     - htop

    runcmd:
     - docker pull cassandra:2.2
    """,

    'ycsb': """#cloud-config

    packages:
     - git
     - openjdk-7-jdk
     - maven
     - htop

    runcmd:
     - git clone https://github.com/joalder/ycsb /home/ubuntu/ycsb
     - chown -R ubuntu:ubuntu /home/ubuntu/ycsb
    """
}

# Standard Python logging dict config
LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(asctime)s %(levelname)s %(message)s'
        },
    },
    'filters': {
        'info-warn': {
            '()': 'cbench.util.LevelFilter',
            'levels': [logging.INFO, logging.WARNING]
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
            'filters': ['info-warn'],
        },
        'console_error': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stderr',
        },
        'file_general': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'cbench.log',
            'formatter': 'verbose',
        },
        'file_action': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'cbench_actions.log',
            'formatter': 'verbose',
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'console_error', 'file_general'],
            'level': 'INFO',
        },
        # This logger is intended for all actions like instance startup, cmds executed etc
        'cbench.actions': {
            'handlers': ['console', 'console_error', 'file_action'],
            'level': 'INFO',
            'propagate': False,
        }
    }
}
