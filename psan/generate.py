from io import StringIO
from xml import sax  # nosec
from xml.sax import make_parser  # nosec
from xml.sax.saxutils import XMLFilterBase, XMLGenerator  # nosec

from flask import (Blueprint, current_app, g, make_response,
                   request)
from flask_babel import gettext

from psan.auth import login_required
from psan.db import get_cursor
from psan.model import AccountType, SubmissionStatus
from psan.submission import get_submission_file
from psan.tool.controller import Controller
from psan.tool.model import AnnotationDecision

_ = gettext

bp = Blueprint("generate", __name__, url_prefix="/generate")


@ bp.route("/output")
@ login_required(role=AccountType.ADMIN)
def output():
    # Parse input params
    submission_uid = request.args.get("doc_uid", type=str)

    min_confidence = current_app.config["RULE_AUTOAPPLY_CONFIDENCE"]

    # Find data in db
    with get_cursor() as cursor:
        # Find ID and document name
        cursor.execute("SELECT id, name FROM submission WHERE uid = %s", (submission_uid,))
        data = cursor.fetchone()
        submission_name = data["name"]
        submission_id = data["id"]

        # Find decisions
        ctl = Controller(cursor, submission_id, g.account["id"])
        decisions = ctl.get_decisions(None, min_confidence, True)

    # Filter secret decisions
    decisions = [dec for dec in decisions if dec["decision"] == AnnotationDecision.SECRET.value]

    # Transform output
    output = StringIO()
    generator = XMLGenerator(output)
    filter = OutputTagFilter(decisions, make_parser())
    filter.setContentHandler(generator)
    # Find submission file
    filename = get_submission_file(submission_uid, SubmissionStatus.RECOGNIZED)
    # Line has to be surrounded with XML tags
    sax.parse(filename, filter)
    # Prepare response
    output = make_response(output.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={submission_name}.out.txt"
    output.headers["Content-type"] = "text/plain"
    return output


class OutputTagFilter(XMLFilterBase):
    """Replace private tokens with replacement"""

    def __init__(self, decisions, parent):
        super().__init__(parent)

        # State of parser
        self._token_id = -1
        self._in_token = True
        self._decisions = decisions
        self._decision_index = 0
        self._replacement_printed = False

    def startElement(self, name, attrs):
        if name == "token":
            self._in_token = True
            self._token_id = int(attrs.get("id"))
            while self._decision_index < len(self._decisions)-1 and self._decisions[self._decision_index]["end"] < self._token_id:
                self._decision_index += 1
                self._replacement_printed = False

    def endElement(self, name):
        if name == "token":
            self._in_token = False

    def characters(self, content):
        decision = self._decisions[self._decision_index]
        if decision["start"] <= self._token_id < decision["end"] or (decision["start"] <= self._token_id <= decision["end"] and self._in_token):
            if not self._replacement_printed:
                super().characters(decision["replacement"])
                self._replacement_printed = True
        else:
            super().characters(content)
