import random
import re
from io import StringIO
from xml import sax
from xml.sax import make_parser
from xml.sax.saxutils import XMLFilterBase, XMLGenerator

from flask import Blueprint, render_template
from flask_babel import gettext
from werkzeug.exceptions import InternalServerError

from psan.auth import login_required
from psan.db import get_db
from psan.model import SubmissionStatus
from psan.submission import get_submission_file

_ = gettext

bp = Blueprint("annotate", __name__, url_prefix="/annotate")


@bp.route("/")
@login_required()
def index():
    # Find longest submission from db
    db = get_db()
    document = db.fetchone(
        "SELECT uid, candidates FROM submission ORDER BY candidates DESC LIMIT 1", ())
    if document:
        # Show first candadate of submission
        return show_candidate(document["uid"], random.randrange(0, document["candidates"]))
    else:
        return render_template("annotate/index.html", candidate=_("No document found..."))


def show_candidate(submission_uid: str, name_entity_id: int):
    # Find line of named entity (NE)
    ne_line = None
    with open(get_submission_file(submission_uid, SubmissionStatus.RECOGNIZED), "r") as input:
        pattern = re.compile(f"<ne[^<>]+id=\"{name_entity_id}\"")
        for line in input:
            if pattern.search(line):
                ne_line = line
                break
    # Check if name_entity_id was found
    if not ne_line:
        raise InternalServerError(
            f"Cannot find name entry {name_entity_id} from submission {submission_uid}")

    # Transform line for UI
    output = StringIO()
    generator = XMLGenerator(output)
    filter = NeTagFilter(name_entity_id, make_parser())
    filter.setContentHandler(generator)
    # Line has to be surrounded with XML tags
    sax.parseString(f"<p>{ne_line}</p>", filter)

    return render_template("annotate/index.html", context_html=output.getvalue(), type=filter.entity_type)


class NeTagFilter(XMLFilterBase):
    """Transform `ne` tags to `mark` tags. Highlight tag with `id==candidate_id`."""

    def __init__(self, candidate_id: int, parent=None):
        super().__init__(parent)

        # Tag to highlight
        self._candidate_id = candidate_id
        self.entity_type = None

    def startElement(self, name, attrs):
        if name == "ne":
            if int(attrs.get("id")) == self._candidate_id:
                self.entity_type = attrs.get("type")
                super().startElement("mark", {"class": "mark-candidate"})
            else:
                super().startElement("mark", {})
        else:
            super().startElement(name, attrs)

    def endElement(self, name):
        if name == "ne":
            super().endElement("mark")
