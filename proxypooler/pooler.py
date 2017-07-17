import argparse
import asyncio
import re
import traceback
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from multiprocessing import Queue
from random import random
from time import sleep, time

from aiohttp import WSCloseCode
from aiohttp.web import Application, WebSocketResponse, WSMsgType, run_app

from proxypooler import config
from proxypooler.errors import ProxyPoolerEmptyError
from proxypooler.ext import conn, deserial, serial, logger, server_logger
from proxypooler.middlewares import (deserialize,
                             make_return, pack, put_in,
                             serialize, unpack, update_expire)
from proxypooler.utils import get_ssl_context
from proxypooler import task_validator


def get_address(request):
    peername = request.transport.get_extra_info('peername')
    if peername is not None:
        host, port = peername
        return '{0}:{1}'.format(host, port)

    return ''

def middleware(calls, is_strip=False):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            item, expire = func(*args, **kwargs)

            if not item:
                return make_return(None, None, is_strip)

            for call in calls:
                item, expire = call(item, expire)
                if not item:
                    break

            return make_return(item, expire, is_strip)
        return wrapper
    return decorate


class Saver:

    def __init__(self, saver_name):
        self.saver_name = saver_name

    def __set__(self, instance, obj):
        if hasattr(obj, 'get') and hasattr(obj, 'put') and hasattr(obj, 'size'):
            instance.__dict__[self.saver_name] = obj
        else:
            raise TypeError('"saver" must has "get"， "put" methods and “size” attr')

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.saver_name]


class ProxyPooler:
    saver = Saver('saver')

    def __init__(self, *, saver=conn):
        self.saver = saver
        self.to_validate = set()
        self.queue = Queue()
        self.regex = re.compile(config.cmd_regex)
        self.pre_empty = False

    def _log_empty(self):
        if not self.pre_empty:
            logger.error('proxypooler was empty')
            self.pre_empty = True

    @middleware(calls=[deserialize])
    def _get_item(self):
        """Get a packed item.
        Returns:
            ({'item': item, 'expire': expire}, expire_)
        The 'expire_' was item's score in sorted set of redis, that was next validate time of item.
        The 'expire' was validate period with item passed in. The same below.
        """
        try:
            item, expire = self.saver.get()
        except ProxyPoolerEmptyError:
            self._log_empty()
            return None, None
        else:
            self.pre_empty = False
            return item, expire

    @middleware(calls=[deserialize])
    def _get_items(self, count, rev=False):
        """Get a list packed items.

        Args:
            count: the number of items expected to be returned.
            rev: get the latest validated items from sorted set in reverse order.

        Returns:
            packed items list such as ([{'item': item, 'expire': expire}, {...}, ...], None)
        """
        if hasattr(self.saver, 'get_list'):
            items = self.saver.get_list(count, rev)
        else:
            items = []
            for _ in range(count):
                try:
                    item = self.saver.get(rev)
                    items.append(item)
                except ProxyPoolerEmptyError:
                    break

        if items:
            self.pre_empty = False
        else:
            self._log_empty()
        return items, None

    @middleware(calls=[unpack])
    def get(self):
        """Get a unpacked item.

        Returns:
            (item, expire)
        """
        return self._get_item()

    @middleware(calls=[unpack], is_strip=True)
    def get_list(self, count, rev=False):
        """Get a list unpacked items.

        Args:
            count: the number of items expected to be returned.
            rev: get the latest validated items from sorted set in reverse order.

        Returns:
            ([(item, expire), (...), ...], None)
        """
        return self._get_items(count, rev)

    @middleware(calls=[pack, serialize, update_expire, put_in])
    def put(self, item, expire):
        """Put a unpacked item with expire as its validate period.

        Returns:
            pass to middlewares.
        """
        return item, expire

    @middleware(calls=[pack, serialize, update_expire, put_in])
    def put_list(self, items):
        """Put a list unpacked items with expire as its validate period.

        Args:
            items: [(item, expire), (...), ...]

        Returns:
            pass to middlewares.
        """
        return items, None

    @middleware(calls=[serialize, put_in])
    def _put_item(self, item, expire):
        """Put a packed item with expire.

        Args:
            items: packed item such as {'item': item, 'expire': expire}
            expire: item's score in sorted set of redis, that was its next validate time.

        Returns:
            pass to middlewares.
        """
        return item, expire

    @middleware(calls=[serialize, put_in])
    def _put_items(self, items):
        """Put a list packed items.

        Args:
            items: [{'item': item, 'expire': expire}, {...}, ...]

        Returns:
            pass to middlewares.
        """
        return items, None

    @property
    def size(self):
        return self.saver.size

    async def handler(self, request):
        """websocket handler.

        Data Format:
            serialized bytes data like [(proxy1, expire), (proxy2, expire), ...].
            The 'expire' was validate period in seconds of proxy.

        Cmd Format:
            'get': return the latest validated proxy.
            'get N': return the latest N(integer type) validated proxies.
        """
        ws = WebSocketResponse()
        await ws.prepare(request)

        request.app['websockets'].append(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    items = deserial(msg.data)
                    if isinstance(items, tuple):
                        server_logger.info("----> got {} item(s)".format(len(items)),
                                           extra={'address': get_address(request)})
                        ws.send_str('ack')
                        self.put_list(items)
                elif msg.type == WSMsgType.TEXT:
                    remote = get_address(request)
                    server_logger.info("----> received cmd {}".format(msg.data),
                                       extra={'address': remote})
                    r = self.regex.match(msg.data)
                    if r is not None:
                        count = r.group(1)
                        count = int(count) if count else 1
                        items = self.get_list(count, rev=True)
                        if items:
                            ws.send_bytes(serial(items))
                            server_logger.info("<---- sent {} item(s)".format(len(items)),
                                               extra={'address': remote})
                            continue
                    ws.send_str('')
                elif (msg.type == WSMsgType.ERROR or
                      msg.type == WSMsgType.CLOSE):
                    break
        except asyncio.CancelledError:
            pass
        except:
            logger.error(traceback.format_exc())
        finally:
            request.app['websockets'].remove(ws)

        return ws
        
    def _get_validates(self):
        """Send expired proxy to validator."""
        while 1:
            items, _ = self._get_items(10)
            if not items:
                break

            item, expire = items[0]
            if expire > time():
                self._put_items(items)
                break

            item, expire = items[-1]
            if expire > time():
                for end, (_, expire) in enumerate(items[1:], start=1):
                    if expire > time():
                        break
                self._put_items(items[end:])
            else:
                end = len(items)

            for item, _ in items[:end]:
                task_validator.validate.delay(item)

    def send_validator(self):
        """Proxy validator."""
        while 1:
            self._get_validates()
            sleep(random())

    def start_server(self, host, port):
        """Server to receive proxies and other commands through websocket."""
        async def on_shutdown(app):  # CTRL+C
            for ws in app['websockets']:
                await ws.close(code=WSCloseCode.GOING_AWAY,
                               message=b'server shutdown')

        if config.ssl_on:
            ssl_context = get_ssl_context()
        else:
            ssl_context = None

        app = Application()
        app['websockets'] = []
        app.router.add_route('GET', '/connect', self.handler)
        app.on_shutdown.append(on_shutdown)
        run_app(app, host=host, port=port, ssl_context=ssl_context,
                print=lambda s: print(s.replace('CTRL+C', 'CTRL+C,CTRL+\\')))

    def start(self):
        """Start validator and server."""
        asyncio_loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        asyncio_loop.run_in_executor(executor, self.send_validator)

        self.start_server(config.local_host, config.local_port)

def run():
    parser = argparse.ArgumentParser(description='Start ProxyPooler')

    parser.add_argument('-v', '--validator', dest='validator', action='store_true',
                        help='start validator')

    parser.add_argument('-s', '--server', dest='server', action='store_true',
                        help='start server')

    args = parser.parse_args()

    p = ProxyPooler()
    logger.info('proxypooler started')
    try:
        if not args.validator and not args.server:
            p.start()
        elif args.validator:
            logger.info('validator start')
            p.send_validator()
        elif args.server:
            logger.info('server start')
            p.start_server(config.local_host, config.local_port)
    finally:
        logger.info('proxypooler stopped')


if __name__ == '__main__':
    run()
