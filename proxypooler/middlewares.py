from time import time

from proxypooler.ext import conn, serial, deserial


def pack(item, expire=None):
    """Pack item and expire into [({'item': item, 'expire': expire}, expire), ...]"""
    if isinstance(item, tuple) or isinstance(item, list):
        item = [({'item': item_, 'expire': expire_}, expire_) for item_, expire_ in item]
    else:
        if expire is None:
            raise TypeError('expire should not be None')
        item = {'item': item, 'expire': expire}

    return item, expire

def unpack(item, expire=None):
    """Unpack item to [(item, expire), ...] or (item, expire)"""
    if isinstance(item, list):
        item = [(item_['item'], item_['expire']) for item_, _ in item]
    else:
        item, expire = item['item'], item['expire']

    return item, expire

def serialize(item, expire):
    """Serialize item.

     Args:
         item: [({'item': item, 'expire': expire}, expire), ...] or {'item': item, 'expire': expire}.
         expire: None or expire as validate period.
    """
    if isinstance(item, list):
        item = [(serial(item_), expire_) for item_, expire_ in item]
    else:
        item = serial(item)

    return item, expire

def deserialize(item, expire):
    """Deserialize item.

     Args:
         item: [(serialized, expire), ...] or serialized.
         expire: None or expire as validate period.
    """
    if isinstance(item, list):
        item = [(deserial(item_), expire_) for item_, expire_ in item]
    else:
        item = deserial(item)

    return item, expire

def update_expire(item, expire):
    """Calculate next validate time.

     Args:
         item: [(serialized, expire), ...] or serialized.
         expire: expire as validate period.
    """
    if isinstance(item, list):
        item = [(item_, int(expire_ + time())) for item_, expire_ in item]
    else:
        expire = int(expire + time())

    return item, expire

def put_in(item, expire, saver=conn):
    """Save item.

     Args:
         item: [(serialized, expire), ...] or serialized.
         expire: None or expire as next validate time.
         saver: container to persistent save item according to the order of the expire.
    """
    if isinstance(item, list):
        if hasattr(saver, 'put_list'):
            saver.put_list(item)
        else:
            for x in item:
                saver.put(*x)
    else:
        saver.put(item, expire)

    return None, None

def make_return(item, expire, is_strip):
    """Whether strip exprie before return."""
    if is_strip:
        return item
    else:
        return item, expire
