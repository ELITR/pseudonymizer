import xml  # nosec - parse only internal XML
import xml.sax  # nosec - parse only internal XML
from io import StringIO
from typing import Dict, List

from flask import Blueprint, current_app, g, make_response, request
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

    parser = xml.sax.make_parser()  # nosec - parse only internal XML
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    handler = OutputTagFilter(decisions, output)
    parser.setContentHandler(handler)
    filename = get_submission_file(submission_uid, SubmissionStatus.RECOGNIZED)
    parser.parse(filename)

    # Prepare response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={submission_name}.out.txt"
    response.headers["Content-type"] = "text/plain"
    return response


class OutputTagFilter(xml.sax.ContentHandler):
    """Replace private tokens with replacement"""

    def __init__(self, decisions: List[Dict[str, str]], output: StringIO):
        super().__init__()

        # State of parser
        self._token_id = -1
        self._in_token = True
        self._decision_index = 0
        self._current_decision = None
        self._replacement_printed = False
        # External data
        self._decisions = decisions
        self._output = output

    def startElement(self, name, attrs):
        if name == "token":
            self._in_token = True
            self._token_id = int(attrs.get("id"))
            while self._decision_index < len(self._decisions)-1 and self._decisions[self._decision_index]["end"] < self._token_id:
                self._decision_index += 1
                self._current_decision = self._decisions[self._decision_index]
                self._replacement_printed = False

    def endElement(self, name):
        if name == "token":
            self._in_token = False

    def characters(self, content):
        if(self._token_id >= 0):
            decision = self._current_decision
            if decision and ((decision["start"] <= self._token_id < decision["end"]) or
                             (decision["start"] <= self._token_id <= decision["end"] and self._in_token)):
                if not self._replacement_printed:
                    if decision["replacement"]:
                        self._output.write(decision["replacement"])
                    self._replacement_printed = True
            else:
                self._output.write(content)
