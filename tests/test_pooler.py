import asyncio
import os
import signal
import ssl
from multiprocessing import Process
from random import randint
from time import sleep
from unittest.mock import Mock

import aiohttp
import pytest
import requests

from proxypooler import config
from proxypooler.pooler import ProxyPooler

from proxypooler.ext import serial, deserial

srv = pytest.mark.skipif(
    not pytest.config.getoption("--runsrv"),
    reason="need --runsrv option to run"
)

if config.ssl_on:
    HOST = 'https://localhost:8090'
else:
    HOST =  'http://localhost:8090'

MAXSIZE = 10**5

@pytest.fixture
def clear(conn):
    yield
    conn.get_list(MAXSIZE)

@pytest.fixture
def ssl_context():
    if config.ssl_on:
        # context = ssl.SSLContext()
        # context.load_cert_chain(CERT, KEY)
        # context.load_verify_locations(CA_CRT)
        # context.verify_mode = ssl.CERT_REQUIRED
        # return context
        return ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, 
                                          cafile=config.ca_crt)
    else:
      return None

@pytest.fixture(scope='function')
def pooler(conn, clear):
    p = ProxyPooler(saver=conn)
    proc = Process(target=p.start)

    yield p, proc

    os.kill(proc.pid, signal.SIGINT)
    proc.join()

@pytest.fixture
def proxy(pooler):

    def send_request():
        host = 'http://localhost:8088'
        count = requests.get('{}/proxies/count'.format(host)).json()['count']
        proxy = requests.get('{}/proxies/{}'.format(host, count)).json()['proxies']
        return count, proxy

    proxy = ["123.163.166.209:808", "175.155.24.9:808", "119.5.1.5:808", 
             "115.220.150.191:808", "117.43.0.73:808", "166.111.77.32:80", 
             "111.13.7.121:80", "125.106.248.222:808", "111.13.2.131:80", 
             "111.13.7.117:80", "119.5.1.35:808", "124.207.82.166:8008", 
             "121.69.47.126:8080", "123.125.212.171:8080", "36.249.24.157:808", 
             "121.232.147.114:9000", "144.12.165.38:808", "218.64.93.47:808", 
             "117.69.7.173:808", "221.229.46.39:808", "113.58.235.73:808", 
             "182.39.1.200:808", "58.50.64.15:808", "220.113.26.18:8080", 
             "117.43.1.187:808", "125.106.249.228:808", "58.253.70.149:8080", 
             "202.108.2.42:80", "106.0.4.116:8081", "175.155.24.22:808", 
             "123.55.189.10:808", "111.13.7.42:83", "121.237.143.107:808", 
             "175.155.25.21:808", "119.5.1.44:808", "27.22.49.236:808", 
             "221.217.34.54:9000", "60.184.174.109:808", "60.184.173.100:808", 
             "59.56.46.133:808", "101.4.136.34:80", "121.204.102.98:808", 
             "113.226.65.175:80", "61.178.238.122:63000", "115.220.146.70:808", 
             "122.241.72.204:808", "175.155.24.2:808", "113.123.127.230:808", 
             "125.106.224.213:808", "117.43.1.246:808", "119.5.1.33:808", 
             "119.5.0.4:808", "119.5.0.70:808", "175.155.25.44:808", 
             "123.55.189.200:808", "180.118.241.227:808", "218.241.234.48:8080", 
             "175.155.25.28:808", "123.163.130.15:808", "119.5.0.22:808"]

    proxy = ["127.0.0.1:{}".format(i+51234) for i in range(300)]
    count = len(proxy)
    count_proxy = Mock(return_value=(count, proxy))
    send_request = count_proxy

    count, proxy = send_request()

    p, proc = pooler
    max_expire = 10

    for i in proxy:
        p.put(i, randint(2, max_expire))

    return p, proc, count


def test_api(conn):
    p = ProxyPooler(saver=conn)
    for i in range(10):
        p.put('127.0.0.1:{}'.format(80+i), i+2)

    p.put_list([('127.0.0.1:{}'.format(80+i), i+2) for i in range(10, 20)])

    assert p.size == 20

    item, expire = p.get()
    assert item == '127.0.0.1:80'

    p.put('127.0.0.1:100', 1)
    item, expire = p._get_item()
    assert item['item'] == '127.0.0.1:100'
    assert item['expire'] == 1

    p._put_item(item, expire)
    item, expire = p.get()
    assert item == '127.0.0.1:100'
    assert expire == 1

    items = [p._get_item() for _ in range(10)]
    p._put_items(items)
    assert p.size == 19

    item, expire = p.get()
    assert item == '127.0.0.1:81'

    item, expire = p._get_item()
    assert item['item'] == '127.0.0.1:82'
    assert item['expire'] == 4

    items = p.get_list(3)
    assert len(items) == 3
    assert items[0][0] == '127.0.0.1:83'
    assert items[0][1] == 5
    assert items[1][1] == 6

    items, _ = p._get_items(5)
    assert len(items) == 5
    assert items[0][0]['item'] == '127.0.0.1:86'

    assert p.size == 9

    items = p.get_list(1)
    assert len(items) == 1
    assert items[0][0] == '127.0.0.1:91'

    items = p.get_list(0)
    assert not items

    items = p.get_list(-2)
    assert not items

    items, _ = p._get_items(1)
    assert len(items) == 1
    assert items[0][0]['item'] == '127.0.0.1:92'

    items, _ = p._get_items(0)
    assert not items

    items = p.get_list(20, rev=True)
    assert len(items) == 7
    assert items[0][0] == '127.0.0.1:99'
    assert p.size == 0

    item, expire = p.get()
    assert item is None

    items, _ = p._get_items(1)
    assert not items

def test_connect(pooler, ssl_context):

    def client_send(data, queue, ssl_context):
        async def _client():
            connector = aiohttp.TCPConnector(ssl_context=ssl_context)
            session = aiohttp.ClientSession(connector=connector)
            async with session.ws_connect('{}/connect'.format(HOST)) as ws:
                if isinstance(data, str):
                    await ws.send_str(data)
                elif isinstance(data, bytes):
                    await ws.send_bytes(data)

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        if msg.data == 'close cmd':
                            await ws.close()
                        break
                    elif msg.type == aiohttp.WSMsgType.BINARY:
                        items = deserial(msg.data)
                        queue.put_nowait(items)
                        break
                    elif (msg.type == aiohttp.WSMsgType.CLOSED or
                        msg.type == aiohttp.WSMsgType.ERROR):
                        break

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_client())

    p, proc = pooler
    proc.start()
    sleep(1) # wait server start


    queue = asyncio.Queue()
    client_send(serial([('127.0.0.1:2017', 20)]), queue, ssl_context)
    assert p.size == 1

    client_send(serial([('127.0.0.1:2018', 40)]), queue, ssl_context)
    client_send('get', queue, ssl_context)
    assert queue.get_nowait()[0] == ('127.0.0.1:2018', 40)

    client_send(serial([('127.0.0.1:2018', 30), ('127.0.0.1:2019', 25), 
                              ('127.0.0.1:2020', 20)]), queue, ssl_context)
    client_send('get 0', queue, ssl_context)
    with pytest.raises(asyncio.QueueEmpty):
        queue.get_nowait()
    assert p.size == 4

    client_send('get proxy', queue, ssl_context)
    assert p.size == 4
    client_send('get 3', queue, ssl_context)
    assert queue.get_nowait() == (('127.0.0.1:2018', 30), ('127.0.0.1:2019', 25), ('127.0.0.1:2020', 20))
    client_send('get 1', queue, ssl_context)
    assert queue.get_nowait() == (('127.0.0.1:2017', 20),)
    assert p.size == 0

@srv
def test_server(monkeypatch, proxy, celery_worker):
    p, proc, count = proxy
    assert p.size == count

    proc.start()
    proc.join(10 + 5) # 60 = count / VALIDATE_COUNT * max_expire

    assert p.size == 0
