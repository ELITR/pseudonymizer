import re

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
        "SELECT uid FROM submission ORDER BY candidates DESC LIMIT 1", ())
    if document:
        # Show first candadate of submission
        return show_candidate(document["uid"], 1)
    else:
        return render_template("annotate/index.html", candidate=_("No document found..."))


def show_candidate(submission_uid: str, name_entity_id: int):
    # Find line of named entity (NE)
    ne_line = None
    with open(get_submission_file(submission_uid, SubmissionStatus.RECOGNIZED), "r") as input:
        pattern = re.compile(f"<ne[^<>]+id={name_entity_id}")
        for line in input:
            if pattern.search(line):
                ne_line = line
                break
    # Check if name_entity_id was found
    if not ne_line:
        raise InternalServerError(
            f"Cannot find name entry {name_entity_id} from submission {submission_uid}")

    # Parse line to UI
    # Mark entity with provided id
    ne_line = re.sub(
        f"<ne[^<>]+id={name_entity_id}>", "<mark class=\"mark-candidate\">", ne_line)
    # Mark remaining entities
    ne_line = re.sub(r"(<|</)ne[^<>]*>", r"\1mark>", ne_line)

    return render_template("annotate/index.html", candidate=ne_line)
