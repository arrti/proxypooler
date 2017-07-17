import os

from celery import Celery
import yaml


app = Celery('proxypooler')
app.config_from_object('proxypooler.celery_config')


class _Config:

    def __init__(self, config_name):
        self.config_name = config_name

    def __set__(self, instance, obj):
        if isinstance(obj, dict):
            instance.__dict__[self.config_name] = obj
        else:
            raise TypeError('config must be a dict')

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.config_name]

class DictConfig:
    config = _Config('config')

    def __init__(self, config):
        self.config = config
        self.attr = config

    def __getattr__(self, name):
        if name in self.config:
            self.attr = self.config.get(name)
            if isinstance(self.attr, dict):
                return DictConfig(self.attr)
            else:
                return self.attr
        else:
            msg = 'config has no attribute {!r}'
            raise AttributeError(msg.format(name))

    def dict(self):
        return self.attr

def load_config(file):
    path = os.getenv('PROXYPOOLER_CONFIG', None)
    if path is None:
        path = '/etc/proxypooler/{}'.format(file)
    else:
        path = '{}/{}'.format(path, file)

    return path

config = DictConfig(yaml.load(open(load_config('proxypooler.yaml'), 'r')))
