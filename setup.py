from distutils.core import setup


setup(name='proxypooler', 
    version='1.0', 
    description='A proxy pool which save proxies and validate them periodically.',
    long_description=None,
    author='arrti', 
    author_email='imxmwd@gmail.com', 
    url='https://github.com/arrti', 
    license='Apache License 2.0',
    keywords='celery proxy',
    packages=['proxypooler'],
    install_requires=['aiohttp', 'celery', 'eventlet', 'msgpack-python',
                      'pika', 'PyYAML', 'redis', 'requests']
)
