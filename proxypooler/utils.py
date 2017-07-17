import ssl

import pika

from proxypooler import config


class LoggerAsync:
    """Logger's async proxy.

    Logging task was sent to celery to run.
    """

    def __init__(self, name, logger):
        self.name = name
        self._logger = logger # celery task

    def debug(self, msg, *args, **kwargs):
        self._logger.delay(self.name, 'debug', msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.delay(self.name, 'info', msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._logger.delay(self.name, 'warning', msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.delay(self.name, 'error', msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self._logger.delay(self.name, 'critical', msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._logger.delay(self.name, 'critical', msg, *args, **kwargs)


class MQueue:
    """ RabbitMQ's publisher/subscriber.

    Attributes:
        exchange: exchange name.
        qname: queue name.
    """

    def __init__(self, type_, url, exchange, qname):
        parameters = pika.URLParameters(url)
        self._connection = pika.BlockingConnection(parameters)
        self.exchange = exchange
        self.qname = qname
        if type_ == 'sub':
            self.channel = self._connection.channel()
            self.channel.exchange_declare(exchange=self.exchange,
                                          type='topic')

            self.channel.queue_declare(queue=self.qname, durable=True)

    def put(self, msg, routing_key):
        """Publish one message."""
        channel = self._connection.channel()
        channel.exchange_declare(exchange=self.exchange,
                                 type='topic')
        try:
            channel.basic_publish(exchange=self.exchange,
                                  routing_key=routing_key,
                                  body=msg,
                                  properties=pika.BasicProperties(
                                      delivery_mode=2,  # make message persistent
                                  ))
        except:
            print('error')
        channel.close()

    def start(self, binding_key, callback):
        """Start subscriber."""
        self.channel.queue_bind(exchange=self.exchange,
                                queue=self.qname,
                                routing_key=binding_key)

        self.channel.basic_consume(callback,
                                   queue=self.qname)
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass
        finally:
            self.channel.close()


def get_ssl_context():
    context = ssl.SSLContext()
    context.load_cert_chain(config.server_cert, config.server_key, config.server_cert_password)
    if config.ca_crt:
        context.load_verify_locations(config.ca_crt)
    else:
        context.load_default_certs(ssl.Purpose.CLIENT_AUTH)
    context.verify_mode = ssl.CERT_OPTIONAL # it was not required to authenticate the client certificate

    return context
