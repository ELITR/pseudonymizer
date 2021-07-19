import os

from flask import Flask

from celery import Celery, Task
from celery_once import QueueOnce


def init_celery(app: Flask) -> None:
    global celery
    celery = Celery(
        app.name,
        backend=os.environ["CELERY_REDIS"],
        broker=os.environ["CELERY_REDIS"],
        include=["psan.celery.pre_process", "psan.celery.re_annotate"]
    )
    celery.conf.update(app.config)
    celery.conf.ONCE = {
        'backend': 'celery_once.backends.Redis',
        'settings': {
            'url': os.environ["CELERY_REDIS"],
            'default_timeout': 60 * 60
        }
    }

    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # Make QueueOnce app context aware.
    class ContextQueueOnce(QueueOnce):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super(ContextQueueOnce, self).__call__(*args, **kwargs)

    celery.QueueOnce = ContextQueueOnce
