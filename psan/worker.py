from psan import celery
from psan.db import commit, get_cursor
from psan.model import SubmissionStatus
from psan.submission import get_submission_file
from psan.tool import recognize_file


@celery.task()
def recognize_submission(uid: str) -> None:
    # Run autorecognition
    input_file = get_submission_file(uid, SubmissionStatus.NEW)
    output_file = get_submission_file(uid, SubmissionStatus.RECOGNIZED)
    num_candidates = recognize_file(input_file, output_file)

    # Update db with candidates
    with get_cursor() as cursor:
        cursor.execute("UPDATE submission SET status = %s, candidates = %s WHERE uid = %s",
                       (SubmissionStatus.RECOGNIZED.value, num_candidates, uid))
        commit()
