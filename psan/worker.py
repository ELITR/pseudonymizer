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

    # Prepare annotation tracking
    with get_cursor() as cursor:
        # Get document ID
        cursor.execute("SELECT id FROM submission WHERE uid = %s", (uid,))
        submission = cursor.fetchone()["id"]

        # Insert annotation entries
        for ne_id in range(num_candidates):
            cursor.execute("INSERT INTO annotation (submission, ne_id) VALUES (%s, %s)", (submission, ne_id))

        commit()

    # Update document status
    with get_cursor() as cursor:
        cursor.execute("UPDATE submission SET status = %s WHERE uid = %s",
                       (SubmissionStatus.RECOGNIZED.value, uid))
        commit()
