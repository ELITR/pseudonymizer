import os

from flask import Flask

from celery import Celery, Task


def init_celery(app: Flask) -> None:
    global celery
    celery = Celery(
        app.name,
        backend=os.environ["CELERY_REDIS"],
        broker=os.environ["CELERY_REDIS"],
        include=["psan.celery.recognize", "psan.celery.decide"]
    )
    celery.conf.update(app.config)

    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
