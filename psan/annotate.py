import random
import re
from io import StringIO
from xml import sax  # nosec
from xml.sax import make_parser  # nosec
from xml.sax.saxutils import XMLFilterBase, XMLGenerator  # nosec

from flask import Blueprint, g, render_template, request
from flask.helpers import url_for
from flask_babel import gettext
from werkzeug.exceptions import InternalServerError
from werkzeug.utils import redirect

from psan.auth import login_required
from psan.db import commit, get_cursor
from psan.model import (AccountType, AnnotateForm, AnnotationDecision,
                        SubmissionStatus)
from psan.submission import get_submission_file

_ = gettext

bp = Blueprint("annotate", __name__, url_prefix="/annotate")

NE_CODES = {"ah": "street numbers", "at": "phone/fax numbers", "az": "zip codes",
            "gc": "states", "gh": "hydronyms", "gl": "nature areas / objects", "gq": "urban parts",
            "gr": "territorial names", "gs": "streets, squares", "gt": "continents", "gu": "cities/towns",
            "g_": "underspecified geographical name", "ia": "conferences/contests", "ic": "cult./educ./scient. inst.",
            "if": "companies, concerns...", "io": "government/political inst.", "i_": "underspecified institutions",
            "me": "email address", "mi": "internet links", "mn": "periodical", "ms": "radio and TV stations",
            "na": "age", "nb": "vol./page/chap./sec./fig. numbers", "nc": "cardinal numbers",
            "ni": "itemizer", "no": "ordinal numbers", "ns": "sport score", "n_": "underspecified number expression",
            "oa": "cultural artifacts (books, movies)", "oe": "measure units", "om": "currency units",
            "op": "products", "or": "directives, norms", "o_": "underspecified artifact name", "pc": "inhabitant names",
            "pd": "(academic) titles", "pf": "first names", "pm": "second names", "pp": "relig./myth persons",
            "ps": "surnames", "p_": "underspecified personal name", "td": "days", "tf": "feasts", "th": "hours",
            "tm": "months", "ty": "years"}


@bp.route("/")
@login_required()
def index():
    # Find longest submission from db
    with get_cursor() as cursor:
        cursor.execute("SELECT uid, COUNT(annotation.id) AS candidates FROM submission "
                       "JOIN annotation ON submission.id=annotation.submission WHERE status = %s "
                       "GROUP BY submission.id", (SubmissionStatus.RECOGNIZED.value,))
        document = cursor.fetchone()
    if document:
        # Show first candadate of submission
        return show_candidate(document["uid"], random.randrange(0, document["candidates"]))  # nosec
    else:
        return render_template("annotate/index.html", candidate=_("No document ready for annotation found..."))


@bp.route("/show")
@login_required(role=AccountType.ADMIN)
def show():
    doc_uid = request.args.get("doc_uid", type=str)
    ne_id = request.args.get("ne_id", type=int)
    return show_candidate(doc_uid, ne_id)


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
    filter = NeTagFilter(submission_uid, name_entity_id, make_parser())
    filter.setContentHandler(generator)
    # Line has to be surrounded with XML tags
    sax.parseString(f"<p>{ne_line}</p>", filter)

    # Show correct NE type string
    if filter.entity_type in NE_CODES:
        type_str = NE_CODES[filter.entity_type]
    else:
        type_str = filter.entity_type

    form = AnnotateForm(request.form)

    return render_template("annotate/index.html", context_html=output.getvalue(), type=type_str,
                           form=form, submission_uid=submission_uid, name_entity_id=name_entity_id)


@bp.route("/set", methods=['POST'])
@login_required()
def set():
    form = AnnotateForm(request.form)
    if form.validate():
        # Process request
        if form.ctx_public.data:
            decision = AnnotationDecision.CONTEXT_PUBLIC
        elif form.ctx_secret.data:
            decision = AnnotationDecision.CONTEXT_SECRET
        elif form.lemma_public.data or form.category_public.data:
            decision = AnnotationDecision.RULE_PUBLIC
        elif form.lemma_secret.data or form.category_secret.data:
            decision = AnnotationDecision.RULE_SECRET
        else:
            raise InternalServerError(f"Unknown annotation {request.form}")

        # Save result to db
        with get_cursor() as cursor:
            cursor.execute("UPDATE annotation SET decision = %s FROM submission "
                           "WHERE submission.uid = %s and submission.id = annotation.submission and "
                           "ne_id = %s", (decision.value, form.submission_uid.data, form.ne_id.data))
            commit()

        # Show another tag
        if g.account["type"] != AccountType.ADMIN.value:
            return redirect(url_for(".index"))
        else:
            return redirect(url_for(".show", doc_uid=form.submission_uid.data, ne_id=form.ne_id.data))
    else:
        return redirect(url_for(".index"))


class NeTagFilter(XMLFilterBase):
    """Transform `ne` tags to `mark` tags. Highlight tag with `id==candidate_id`."""

    def __init__(self, uid: str, candidate_id: int, parent=None):
        super().__init__(parent)

        # Tag to highlight
        self._uid = uid
        self._candidate_id = candidate_id
        self.entity_type = None

    def startElement(self, name, attrs):
        if name == "ne":
            # Test it for candidate
            if int(attrs.get("id")) == self._candidate_id:
                self.entity_type = attrs.get("type")
                new_attrs = {"class": "ne-candidate"}
            else:
                new_attrs = {"class": "ne"}
            # Update UI for administrator
            if(g.account["type"] == AccountType.ADMIN.name):
                new_attrs["onClick"] = "showNameEntryId(event, \"%s\", %d)" % (
                    self._uid, int(attrs["id"]))
            # Pass updated element
            super().startElement("mark", new_attrs)
        else:
            super().startElement(name, attrs)

    def endElement(self, name):
        if name == "ne":
            super().endElement("mark")
