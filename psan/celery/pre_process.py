from psan.celery import celery
from psan.db import commit, get_cursor
from psan.model import SubmissionStatus
from psan.submission import get_submission_file
from psan.tool import controller
from psan.tool.task.pre_annotate import detect_recognized_name_entries
from psan.tool.task.re_annotate import apply_rules
from psan.tool.task.recognize import recognize_file


@celery.task()
def pre_process(document_id: int) -> None:
    with get_cursor() as cursor:
        cursor.execute("SELECT uid FROM submission WHERE id = %s", (document_id,))
        uid = cursor.fetchone()["uid"]

    # Input recognized file
    input_file = get_submission_file(uid, SubmissionStatus.NEW)
    recognized_file = get_submission_file(uid, SubmissionStatus.RECOGNIZED)

    # Run recognition
    num_tokens = recognize_file(input_file, recognized_file)

    with get_cursor() as cursor:
        ctl = controller.Controller(cursor, document_id)

        # Run pre-annotation
        detect_recognized_name_entries(recognized_file, ctl)

        # Re-annotate
        apply_rules(recognized_file, ctl)

        # Update document status
        cursor.execute("UPDATE submission SET status = %s, num_tokens = %s WHERE id = %s",
                       (SubmissionStatus.RECOGNIZED.value, num_tokens, document_id))
        commit()
