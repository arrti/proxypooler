import pytest

from proxypooler.errors import ProxyPoolerEmptyError

def test_db(conn):
    conn.put('127.0.0.1:80', 15)
    conn.put('127.0.0.1:81', 14)
    conn.put('127.0.0.1:82', 210)
    conn.put('127.0.0.1:83', 2)
    conn.put('127.0.0.1:84', 100)

    assert conn.size == 5
    ip = conn.get()[0].decode('utf-8')
    assert ip == '127.0.0.1:83'
    ip = conn.get()[0].decode('utf-8')
    assert ip == '127.0.0.1:81'
    assert conn.size == 3

    ips = conn.get_list(30)
    assert len(ips) == 3
    ip = ips[0][0].decode('utf-8')
    assert ip == '127.0.0.1:80'
    ip = ips[1][0].decode('utf-8')
    assert ip == '127.0.0.1:84'
    ip = ips[2][0].decode('utf-8')
    assert ip == '127.0.0.1:82'
    assert conn.size == 0

    conn.put('127.0.0.1:83', 2)
    conn.put('127.0.0.1:83', 20)
    assert conn.size == 1
    ip, expire = conn.get()
    assert ip.decode('utf-8') == '127.0.0.1:83'
    assert expire == 20

    conn.put('127.0.0.1:83', 20)
    conn.put_list([('127.0.0.1:84', 100), ('127.0.0.1:81', 14), ('127.0.0.1:82', 210)])
    assert conn.size == 4
    ip = conn.get()[0].decode('utf-8')
    assert ip == '127.0.0.1:81'
    ip = conn.get()[0].decode('utf-8')
    assert ip == '127.0.0.1:83'

    ips = conn.get_list(2, rev=True)
    assert len(ips) == 2
    assert ips[0][0].decode('utf-8') == '127.0.0.1:82'
    assert ips[0][1] == 210
    assert ips[1][0].decode('utf-8') == '127.0.0.1:84'
    assert ips[1][1] == 100
    assert conn.size == 0

def test_db_empty(conn):
    with pytest.raises(ProxyPoolerEmptyError):
        conn.get()
