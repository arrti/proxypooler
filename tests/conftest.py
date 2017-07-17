import sys
from pathlib import Path

import pytest


# add project path to sys.path in case 'proxypooler' was not installed
current = Path(__file__).parent.parent
path = str(current)
sys.path.append(path)
    

def pytest_addoption(parser):
    parser.addoption("--runsrv", action="store_true",
                     help="run server tests, need proxypool's server")

@pytest.fixture(scope='session')
def conn():
    from proxypooler.db import RedisClient as rc
    return rc('127.0.0.1', 6379) # make sure it was running before testing

@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url' : 'amqp://guest:guest@localhost:5672//',
        'result_backend' : 'redis://127.0.0.1:6379/1' ,

        'timezone' : 'Asia/Shanghai' ,

        'worker_pool': 'eventlet',

        'worker_concurrency' : 300,

        'imports' : (
            'proxypooler.task_validator',
            'proxypooler.task_logger'
        ),

        'result_expires' : 10
    }
