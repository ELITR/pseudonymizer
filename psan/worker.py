
import time
from psan import celery
from psan.db import get_db


@celery.task()
def recognize_submission(uid: str) -> None:
    time.sleep(10)
    db = get_db()
    db.execute("UPDATE submission SET name = %s WHERE uid = %s",
               ("done", uid))
    db.commit()
