import logging.config
from pathlib import Path

from celery import task
import yaml

from proxypooler import config, load_config


# do not load logging.yaml in __init__.py
PROJECT_ROOT = Path(__file__).parent
logging.config.dictConfig(
            yaml.load(open(load_config('logging.yaml'), 'r')))

server_logger = logging.getLogger('server_logger')
server_debug_logger = logging.getLogger('server_debug_logger')
debug_logger = logging.getLogger('debug_logger')
file_logger = logging.getLogger('file_logger')

@task()
def log(name, lvl, msg, *args, **kwargs):
    if name == config.project_srv:
        logger_file = server_logger
        logger_stream = server_debug_logger
    else:
        logger_file = file_logger
        logger_stream = debug_logger

    if config.debug:
        getattr(logger_stream, lvl, 'info')(msg, *args, **kwargs) # logging to stream
    if name == config.project_srv:
        getattr(logger_file, lvl, 'info')(msg, *args, **kwargs) # server logging everything to file
    if lvl in ('error', 'critical'):
        getattr(logger_file, lvl, 'error')(msg, *args, **kwargs) # only logging  errors
