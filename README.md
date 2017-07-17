# ProxyPooler: 一个基于Celery的异步/分布式代理存储/验证器
[![Build Status](https://travis-ci.org/arrti/proxypooler.svg?branch=master)](https://travis-ci.org/arrti/proxypooler)

传入代理和它的验证周期，proxypooler会将其存储并在代理验证周期到来时验证代理的有效性，直到失效时才将其移除。不同的代理可以配置不同的验证周期。 Celery使用Eventlet实现并发。   
本项目可以作为其他项目的一个模块使用，也可以作为一个独立的服务通过websocket进行通信。    
可以通过自定义后台存储、序列化/反序列化函数、定期执行的函数（作为Celery的任务）等来周期性地处理你存入的其他类型数据。


## 模块功能描述
* `pooler.py`
  * `validator`代理验证器：从存储（默认是redis）中取出到期的代理，将其发送给celery进行验证；
  * `server`服务器：通过websocket协议接收代理，可能是新的代理，也可能是通过验证的代理。服务器的地址和端口由配置文件中的`local_*`来指定。支持SSL。
  * `ProxyPooler`类：核心类，实现了上述验证器和服务器，同时提供了类似于下面的websocket的接口，可用于存储或获取代理，具体见模块注释。

* `celery`服务  
  * `task_validator.py`：代理有效性验证任务，通过验证的代理会发送到rabbitmq的`proxypooler_validator_queue`队列（exchange为`proxypooler_validator_exchange`）中等待后续处理；
  * `task_logger.py`：日志任务，所有的日志信息都通过该任务来输出到终端或文件。
  
* `sender.py`  
从rabbitmq的`proxypooler_validator_queue`队列读取通过验证的代理，使用websocket协议将其发送到配置文件中`remote_*`指定的地址和端口处（默认等于`local_*`）。

**注意：** 接收到的新代理不会立即验证，而是会等到下一个验证周期（验证周期 + 收到代理的时间）才进行验证。


## 使用

### pooler模块的命令行參數
* `-v`:  仅启动代理验证器，会将验证任务发送给celery执行；
* `-s`:  仅启动服务器，通过webocket接收代理。

不带任何参数则同时启动验证器和服务器，2个参数都有则只启动验证器。

### 配置
项目的配置在`proypooler.yaml`中；celery的配置在`celery_config.py`中；logger的配置在`logging.yaml`中。
默认会在环境变量`PROXYPOOLER_CONFIG`指定的目录或`/etc/proxypooler`目录下寻找`proypooler.yaml`和`logging.yaml`文件。
按需修改相应的参数即可。

### 启动
首先设置环境变量`PROXYPOOLER_CONFIG`为`proxypooler/proxypooler`目录或将2个`*.yaml`配置文件拷贝到`/etc/proxypooler`目录下。然后按顺序在3个终端中执行执行：  
(1) 启动celery服务  
下面的命令会启动300个协程来并发执行任务（验证和日志任务）
```
celery -A proxypooler worker -P eventlet -c 300
```
(2) 启动pooler
```
python run_pooler.py
```
(3) 启动sender
```
python run_sender.py
```

推荐使用[supervisord](http://supervisord.org/)来管理上面3个进程，supervisord的配置文件在`supervisor`目录下，使用前务必修改相应的参数。  

### websocket api
* 数据格式  
使用`ext.py`模块中的`serial`函数将形如`[(代理1, 验证周期秒数), (代理2, 验证周期秒数), ...]`序列化后得到的二进制数据。`deserial`是对应的反序列化函数（默认使用[MessagePack](http://msgpack.org/)）。
* 命令格式
  * `get`：获取1个最新验证过的代理；
  * `get N`：获取 N 个最新验证过的代理。    
上述命令皆为文本字符串。


## 测试
下面2种方法任选其一即可。
### tox
使用`tox`进行集成测试。  
首先安装`tox`：
```
pip install tox
```
然后在`proxypooler`目录下执行`tox`命令，通过测试则说明一切正常。


### pytest
首先安装`pytest`：
```
pip install pytest
```
然后在`proxypooler`目录下执行`pytest tests --runsrv`命令，通过测试则说明一切正常。
