from functools import partial

import msgpack

from proxypooler import config
from proxypooler.task_logger import log
from proxypooler.utils import LoggerAsync, MQueue
from proxypooler.db import RedisClient


conn = RedisClient()

serial = msgpack.packb # use MessagePack as serializer
deserial = partial(msgpack.unpackb, encoding='utf-8', use_list=False)

logger = LoggerAsync(config.project, log)
server_logger = LoggerAsync(config.project_srv, log)

validator_pub_queue = MQueue('pub', config.mq_url,
                             'proxypooler_validator_exchange', 'proxypooler_validator_queue')
validator_sub_queue = MQueue('sub', config.mq_url,
                             'proxypooler_validator_exchange', 'proxypooler_validator_queue')
