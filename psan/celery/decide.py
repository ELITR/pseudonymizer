import functools
from typing import Optional, Tuple

from psan.celery import celery
from psan.db import commit, get_cursor
from psan.model import AnnotationDecision, RuleType, SubmissionStatus
from psan.submission import get_submission_file
from psan.tool.annotater import auto_decide_file
from psan.tool.model import Candidate, Evidence, ReasonType, Rule, Word


@celery.task()
def auto_decide_remaining(doc_id: int) -> None:
    with get_cursor() as cursor:
        # Get submission file
        cursor.execute("SELECT uid FROM submission WHERE id = %s", (doc_id,))
        uid = cursor.fetchone()["uid"]
        submission_file = get_submission_file(uid, SubmissionStatus.RECOGNIZED)

        # Parse file and apply rules
        reason_find = functools.partial(_find_decision_reason, doc_id=doc_id, cursor=cursor)
        rule_find = functools.partial(_find_rule, cursor=cursor)
        lookup = functools.partial(_word_lookup, cursor=cursor)
        update = functools.partial(_update_annotation, doc_id=doc_id, cursor=cursor)
        auto_decide_file(submission_file, reason_find, rule_find, lookup, update)

        commit()


def _find_rule(evidence: Evidence, cursor) -> Optional[Rule]:
    """Finds rule in DB according to evidence"""
    if evidence.type == ReasonType.NE_TYPE:
        cursor.execute("SELECT id FROM rule WHERE type = %s and condition = %s",
                       (RuleType.NE_TYPE.value, evidence.value))
    elif evidence.type == ReasonType.WORD_TYPE:
        cursor.execute("SELECT id FROM rule WHERE type = %s and condition = %s",
                       (RuleType.WORD_TYPE.value, evidence.value))
    # Returns rule or None
    row = cursor.fetchone()
    if row:
        return Rule(row["id"])
    else:
        return None


def _word_lookup(word: Word, cursor) -> Tuple[ReasonType, int]:
    """ Decides how many words following `word` should be captured for next evidence."""
    cursor.execute("SELECT condition[1] AS first_word, max(array_length(condition, 1)) as length FROM rule"
                   " WHERE condition[1] = %s GROUP BY first_word", (word.token,))
    row = cursor.fetchone()
    if row:
        return ReasonType.WORD_TYPE, row["length"] - 1
    else:
        return ReasonType.NONE, 0


def _update_annotation(candidate: Candidate, rule: Rule, doc_id: int, cursor) -> None:
    cursor.execute("INSERT INTO annotation(submission, ref_start, ref_end, decision, rule) VALUES(%s, %s, %s, %s, %s)"
                   " ON CONFLICT(submission, ref_start, ref_end) DO UPDATE SET decision=excluded.decision, rule=excluded.rule",
                   (doc_id, candidate.start, candidate.end, AnnotationDecision.RULE.value, rule.id))


def _find_decision_reason(candidate: Candidate, doc_id: int, cursor) -> ReasonType:
    # Finds decision in DB
    cursor.execute("SELECT annotation.decision AS decision, type FROM annotation LEFT JOIN rule ON annotation.rule=rule.id"
                   " WHERE submission = %s and ref_start = %s and ref_end = %s",
                   (doc_id, candidate.start, candidate.end))
    row = cursor.fetchone()
    # Translate DB entry to ReasonType
    if row is None or row["decision"] == AnnotationDecision.UNDECIDED.value:
        return ReasonType.NONE
    elif row["type"] is None:
        return ReasonType.CONTEXT
    elif row["type"] == RuleType.WORD_TYPE.value:
        return ReasonType.WORD_TYPE
    elif row["type"] == RuleType.LEMMA.value:
        return ReasonType.LEMMA
    elif row["type"] == RuleType.NE_TYPE.value:
        return ReasonType.NE_TYPE
    # Every decission should be mapped
    raise RuntimeError(f"Unknown candidate {candidate} decision reason type {row['type']}")
