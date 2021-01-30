import functools
from typing import Container, Optional

from psan.celery import celery
from psan.db import commit, get_cursor
from psan.model import AnnotationDecision, RuleType, SubmissionStatus
from psan.submission import get_submission_file
from psan.tool import auto_decide_file
from psan.tool.model import Candidate, Evidence, Rule


@celery.task()
def auto_decide_remaining(doc_id: int) -> None:
    with get_cursor() as cursor:
        # Get submission file
        cursor.execute("SELECT uid FROM submission WHERE id = %s", (doc_id,))
        uid = cursor.fetchone()["uid"]
        submission_file = get_submission_file(uid, SubmissionStatus.RECOGNIZED)

        # Parse file and apply rules
        find = functools.partial(find_rule, cursor=cursor)
        update = functools.partial(update_annotation, doc_id=doc_id, cursor=cursor)
        auto_decide_file(submission_file, SqlContainer(doc_id, cursor), find, update)

        commit()


def find_rule(evidence: Evidence, cursor) -> Optional[Rule]:
    cursor.execute("SELECT id FROM rule WHERE (type = %s and condition = %s) or (type = %s and condition = %s)"
                   " ORDER BY array_position(array['WORD_TYPE','LEMMA','NE_TYPE'], type::text) LIMIT 1",
                   (RuleType.WORD_TYPE.value, " ".join(evidence.tokens), RuleType.NE_TYPE.value, evidence.ne_type))
    row = cursor.fetchone()
    if row:
        return Rule(row["id"])
    else:
        return None


def update_annotation(candidate: Candidate, rule: Rule, doc_id: int, cursor) -> None:
    cursor.execute("UPDATE annotation SET decision = %s, rule = %s"
                   " WHERE submission = %s and ref_start = %s and ref_end = %s",
                   (AnnotationDecision.RULE.value, rule.id, doc_id, candidate.start, candidate.end))


class SqlContainer(Container[Candidate]):
    def __init__(self, doc_id: int, cursor) -> None:
        self._doc_id = doc_id
        self._cursor = cursor
        super().__init__()

    def __contains__(self, candidate: Candidate) -> bool:
        self._cursor.execute("SELECT decision FROM annotation WHERE submission = %s and ref_start = %s and ref_end = %s",
                             (self._doc_id, candidate.start, candidate.end))
        row = self._cursor.fetchone()
        if row and row["decision"] == AnnotationDecision.UNDECIDED.value:
            return True
        else:
            return False
