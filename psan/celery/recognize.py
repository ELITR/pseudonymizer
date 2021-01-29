import xml.sax  # nosec - parse only internal XML
import xml.sax.handler  # nosec - parse only internal XML
from typing import List, NamedTuple

from psan.celery import celery, decide
from psan.db import commit, get_cursor
from psan.model import AnnotationDecision, SubmissionStatus
from psan.submission import get_submission_file
from psan.tool import recognize_file
from psycopg2.extras import execute_values


@celery.task()
def recognize_submission(uid: str) -> None:
    # Run autorecognition
    input_file = get_submission_file(uid, SubmissionStatus.NEW)
    output_file = get_submission_file(uid, SubmissionStatus.RECOGNIZED)
    num_tokens = recognize_file(input_file, output_file)

    # Prepare annotation tracking
    with get_cursor() as cursor:
        # Get document ID
        cursor.execute("SELECT id FROM submission WHERE uid = %s", (uid,))
        document_id = cursor.fetchone()["id"]

        # Save candidates to db
        parser = xml.sax.make_parser()  # nosec - parse only internal XML
        parser.setFeature(xml.sax.handler.feature_namespaces, 0)
        handler = RecognizedInputHandler(document_id)
        parser.setContentHandler(handler)
        parser.parse(output_file)

        # Insert annotation entries
        execute_values(cursor, "INSERT INTO annotation (submission, ref_start,"
                       " ref_end, decision) VALUES %s ", handler.entities)

        commit()

    # Apply known rules to submission
    decide.auto_decide_remaining(document_id)

    # Update document status
    with get_cursor() as cursor:
        cursor.execute("UPDATE submission SET status = %s, num_tokens = %s WHERE id = %s",
                       (SubmissionStatus.RECOGNIZED.value, num_tokens, document_id))
        commit()


class NameEntry(NamedTuple):
    doc_id: int
    start: int
    end: int
    decision: AnnotationDecision


class RecognizedInputHandler(xml.sax.ContentHandler):
    def __init__(self, document_id: int) -> None:
        super().__init__()
        self._doc_id = document_id
        self._ne_depth = 0
        self.entities: List[NameEntry] = []

    def _register_candidate(self, start_id: int, end_id: int):
        self.entities.append(NameEntry(self._doc_id, start_id, end_id, AnnotationDecision.UNDECIDED.value
                                       if self._ne_depth == 1 else AnnotationDecision.NESTED.value))

    def startElement(self, tag, attributes):
        if tag == "ne":
            self._ne_depth += 1
            self._register_candidate(int(attributes["start"]), int(attributes["end"]))

    def endElement(self, tag):
        if tag == "ne":
            self._ne_depth -= 1
