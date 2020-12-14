
import time

from psan import celery
from psan.db import get_db
from psan.model import SubmissionStatus


@celery.task()
def recognize_submission(uid: str) -> None:
    time.sleep(10)
    db = get_db()
    db.execute("UPDATE submission SET status = %s WHERE uid = %s",
               (SubmissionStatus.RECOGNIZED.value, uid))
    db.commit()
