broker_url = 'amqp://guest:guest@localhost:5672//'  # set rabbitmq as Broker
result_backend = 'redis://127.0.0.1:6379/1'  # set redis as Backend

timezone = 'Asia/Shanghai'                     # set timeone

imports = (                                  # import tasks
    'proxypooler.task_validator', # validator task, to validate proxy
    'proxypooler.task_logger',    # logger task
)

result_expires = 300 # time (in seconds) for when after stored task tombstones will be deleted
