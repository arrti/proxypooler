from random import choice

import requests
from celery import task

from proxypooler import config
from proxypooler.ext import serial
from proxypooler.ext import logger, validator_pub_queue


@task()
def validate(item):
    proxy, expire = item['item'], item['expire']
    logger.info('-proxy: {0}'.format(proxy))
    proxies = {'http': proxy}
    headers = config.headers.dict()
    headers['User-Agent'] = choice(config.user_agent)
    headers['Pragma']  = 'no-cache'
    try:
        response = requests.get(config.validate_url, headers=headers,
                                proxies=proxies, timeout=config.validate_timeout)
        if response.status_code != 200:
            logger.info('proxy {} expired'.format(proxy))
        else:
            msg = serial([(proxy, expire)])
            validator_pub_queue.put(msg, 'proxypooler.validator.passed') # validated proxies put into rabbitmq
            logger.info('proxy {} passed'.format(proxy))
    except requests.exceptions.RequestException as exc:
        logger.warning('proxy {0} expired with error: {1!r}'.format(proxy, exc))
