import os

from psan import celery
from psan.db import get_db
from psan.model import SubmissionStatus
from psan.submission import INPUT_FILENAME, get_submission_folder
from psan.tool import recognize_file


@celery.task()
def recognize_submission(uid: str) -> None:
    db = get_db()

    # Run autorecognition
    folder = get_submission_folder(uid)
    input_file = os.path.join(folder, INPUT_FILENAME)
    output_file = os.path.join(folder, "01.txt")
    num_candidates = recognize_file(input_file, output_file)

    # Update db with candidates
    db.execute("UPDATE submission SET status = %s, candidates = %s WHERE uid = %s",
               (SubmissionStatus.RECOGNIZED.value, num_candidates, uid))
    db.commit()
