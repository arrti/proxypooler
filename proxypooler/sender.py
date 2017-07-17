import asyncio
import os
import signal
import ssl
from multiprocessing import Process, Queue, Event
import traceback

import aiohttp
from async_timeout import timeout

from proxypooler import config
from proxypooler.ext import validator_sub_queue, logger
from proxypooler.errors import ProxyPoolerStoppedError


send_queue = Queue()

def get_ssl_context():
    return ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH,
                                      cafile=config.ca_crt) # verify the server certificate

if config.ssl_on:
    HOST = 'https://{}:{}'.format(config.remote_host, config.remote_port)
    ssl_context = get_ssl_context() # use ssl
else:
    HOST = 'http://{}:{}'.format(config.remote_host, config.remote_port)
    ssl_context = None

stop_flag = Event()

async def client():
    """Send validated proxies to server through websocket."""
    connector = aiohttp.TCPConnector(ssl_context=ssl_context)
    session = aiohttp.ClientSession(connector=connector)
    closing = False
    async with session.ws_connect('{}/connect'.format(HOST)) as ws:
        while not closing:
            item, method = send_queue.get()
            await ws.send_bytes(item)
            try:
                with timeout(10):  # wait for ack or other cmd
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            if msg.data == 'close':
                                await ws.close()
                                closing = True
                                break
                            elif msg.data == 'ack':
                                # send acknowledgment to rabbitmq
                                validator_sub_queue.channel.basic_ack(delivery_tag=method.delivery_tag)
                                break
                        elif (msg.type == aiohttp.WSMsgType.CLOSED or
                              msg.type == aiohttp.WSMsgType.ERROR):
                            closing = True
                            break
            except asyncio.TimeoutError:
                pass


def send():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while 1:
        try:
            loop.run_until_complete(client())
        except:
            logger.error(traceback.format_exc())
        finally:
            stop_flag.set() # client exit unexpectedly
            break


def callback(ch, method, properties, body):
    """Get validated proxy from rabbitmq and pass to client."""
    if not stop_flag.is_set(): # stop rabbitmq subscriber after client exit unexpectedly
        send_queue.put((body, method))
    else:
        raise ProxyPoolerStoppedError('sender stopped unexpectedly')


def run():
    proc = Process(target=send)
    try:
        proc.start()
        validator_sub_queue.start('proxypooler.validator.passed', callback) # start rabbitmq subscriber
    except:
        logger.error(traceback.format_exc())
    finally:
        if not stop_flag.is_set():
            os.kill(proc.pid, signal.SIGINT)


if __name__ == '__main__':
    run()
