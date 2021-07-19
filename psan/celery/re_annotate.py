from psan.celery import celery
from psan.db import commit, get_cursor
from psan.model import SubmissionStatus
from psan.submission import get_submission_file
from psan.tool import controller
from psan.tool.task.re_annotate import apply_rules


@celery.task()
def re_annotate(doc_id: int) -> None:
    with get_cursor() as cursor:
        # Get submission file
        cursor.execute("SELECT uid FROM submission WHERE id = %s", (doc_id,))
        uid = cursor.fetchone()["uid"]
        submission_file = get_submission_file(uid, SubmissionStatus.RECOGNIZED)

        ctl = controller.Controller(cursor, doc_id)

        # Parse file and apply rules
        apply_rules(submission_file, ctl)

        commit()


@celery.task(base=celery.QueueOnce, once={'keys': []})
def re_annotate_all(skip_doc_id: int) -> None:
    with get_cursor() as cursor:
        # Get submission file
        cursor.execute("SELECT id,uid FROM submission WHERE status = %s", (SubmissionStatus.PRE_ANNOTATED.value,))
        for row in cursor:
            id = row["id"]
            uid = row["uid"]
            if skip_doc_id == id:
                continue

            submission_file = get_submission_file(uid, SubmissionStatus.RECOGNIZED)
            with get_cursor() as cur:
                ctl = controller.Controller(cur, id)

                # Parse file and apply rules
                apply_rules(submission_file, ctl)
                commit()
