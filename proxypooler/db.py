import redis

from proxypooler import config
from proxypooler.errors import ProxyPoolerEmptyError


class RedisClient:
    """Underlying storage unit.
    
    Save Item object and its expire time in redis.
    """

    def __init__(self, host=config.redis_host, port=config.redis_port):
        self._db = redis.Redis(host=host, port=port)

    def get(self):
        """Get single item from pool.

        Returns:
             (item, expire).

        Raises:
            ProxyPoolEmptyError.
        """
        try:
            # timeout return None, otherwise return bytes data
            item = self._db.zrange(config.pool_name, 0, 0)[0]
            expire = self._db.zscore(config.pool_name, item) # float
            self._db.zrem(config.pool_name, item)
            return item, expire
        except IndexError:
            raise ProxyPoolerEmptyError('proxypooler was empty') from None

    def get_list(self, count=1, rev=False):
        """Get item list from pool.

        Args:
            the length of item list.

        Returns:
            (item, expire) list, like: [(item1, expire1), ..., (itemN, expireN)].
        """
        if count <= 0:
            return []

        if not rev:
            items = self._db.zrange(config.pool_name, 0, count - 1)
        else:
            items = self._db.zrevrange(config.pool_name, 0, count - 1) # the last
        items_expires = [(item, self._db.zscore(config.pool_name, item)) for item in items]
        if items:
            self._db.zrem(config.pool_name, *items)
        return items_expires

    def put(self, item, expire):
        self._db.zadd(config.pool_name, item, expire) # name和score 与redis官方命令的顺序相反

    def put_list(self, items):
        for item, expire in items:
            self.put(item, expire)

    @property
    def size(self):
        return self._db.zcard(config.pool_name)
