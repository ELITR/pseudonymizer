import json
from io import StringIO
from xml import sax  # nosec
from xml.sax import make_parser  # nosec
from xml.sax.saxutils import XMLFilterBase, XMLGenerator  # nosec

from flask import Blueprint, g, jsonify, render_template, request
from flask.helpers import url_for
from flask_babel import gettext
from werkzeug.exceptions import BadRequest
from werkzeug.utils import redirect

from psan.auth import login_required
from psan.db import commit, get_cursor
from psan.model import (AccountType, AnnotateForm, AnnotationDecision,
                        ReferenceType, RuleType, SubmissionStatus)
from psan.submission import get_submission_file

_ = gettext

bp = Blueprint("annotate", __name__, url_prefix="/annotate")


@bp.route("/")
@login_required()
def index():
    # Find longest submission from db
    with get_cursor() as cursor:
        cursor.execute("SELECT submission.id, COUNT(annotation.id) AS candidates FROM submission "
                       "JOIN annotation ON submission.id = annotation.submission and decision = %s "
                       "WHERE status = %s GROUP BY submission.id",
                       (AnnotationDecision.UNDECIDED.value, SubmissionStatus.RECOGNIZED.value))
        document = cursor.fetchone()
        if document:
            # Show first candadate of submission
            cursor.execute("SELECT * FROM annotation WHERE submission = %s and decision = %s LIMIT 1",
                           (document["id"], AnnotationDecision.UNDECIDED.value))
            candidate = cursor.fetchone()
            return show_candidate(candidate["submission"], candidate["ref_start"], candidate["ref_end"])
        else:
            return render_template("annotate/index.html", context_html=_("No document ready for annotation found..."),
                                   form=AnnotateForm())


@bp.route("/show")
@login_required(role=AccountType.ADMIN)
def show():
    # Parse input params
    doc_id = request.args.get("doc_id", type=int)
    ref_start = request.args.get("ref_start", type=int)
    ref_end = request.args.get("ref_end", type=int)
    if doc_id is None or ref_start is None or ref_end is None:
        raise BadRequest("Missing required parameters")
    # Show annotation page
    return show_candidate(doc_id, ref_start, ref_end)


def show_candidate(submission_id: int, ref_start: int, ref_end: int):
    # Prepare window size
    win_start = max(ref_start - 200, 0)
    win_end = ref_start + 200
    # Prepare web page
    form = AnnotateForm(request.form)

    return render_template("annotate/index.html", form=form, submission_id=submission_id,  win_start=win_start, win_end=win_end,
                           highlight_start=ref_start, highlight_end=ref_end)


@bp.route("/window")
@login_required()
def window():
    # Parse input params
    submission_id = request.args.get("doc_id", type=int)
    start = request.args.get("start", type=int)
    end = request.args.get("end", type=int)
    if submission_id is None or start is None or end is None:
        raise BadRequest(f"Missing required parameters {submission_id}, {start}, {end}")

    # Find UID
    with get_cursor() as cursor:
        cursor.execute("SELECT uid FROM submission WHERE id = %s", (submission_id,))
        submission_uid = cursor.fetchone()["uid"]
    filename = get_submission_file(submission_uid, SubmissionStatus.RECOGNIZED)

    # Transform line for UI
    output = StringIO()
    generator = XMLGenerator(output)
    filter = RecognizedTagFilter(start, end, make_parser())
    filter.setContentHandler(generator)
    # Line has to be surrounded with XML tags
    sax.parse(filename, filter)

    return output.getvalue()


@bp.route("/decisions")
@login_required()
def decisions():
    # Parse input params
    submission_id = request.args.get("doc_id", type=int)
    window_start = request.args.get("start", type=int)
    window_end = request.args.get("end", type=int)
    if submission_id is None or window_start is None or window_end is None:
        raise BadRequest(f"Missing required parameters {submission_id}, {window_start}, {window_end}")

    # Returns decision in defined interval
    decisions = []
    with get_cursor() as cursor:
        cursor.execute("SELECT ref_start, ref_end, COALESCE(rule.decision::text, annotation.decision::text) as decision"
                       " FROM annotation LEFT JOIN rule ON annotation.rule = rule.id"
                       " WHERE submission = %s and (%s<=ref_start and ref_start<=%s) and annotation.decision != %s"
                       " ORDER BY ref_start",
                       (submission_id, window_start, window_end, AnnotationDecision.NESTED.value))
        for row in cursor:
            decisions.append({"start": row["ref_start"], "end": row["ref_end"], "decision": row["decision"]})

    return jsonify(decisions)


@bp.route("/set", methods=['POST'])
@login_required()
def set():
    form = AnnotateForm(request.form)
    if form.validate():
        # Process decision
        if form.ctx_public.data or form.lemma_public.data or form.ne_type_public.data:
            decision = AnnotationDecision.PUBLIC
        else:
            decision = AnnotationDecision.SECRET
        # Process decision condition
        if form.lemma_public.data or form.lemma_secret.data:
            rule = RuleType.WORD_TYPE
            rule_condition = json.loads(form.condition.data)
        elif form.ne_type_public.data or form.ne_type_secret.data:
            rule = RuleType.NE_TYPE
            rule_condition = [form.ne_type.data]
        else:
            rule = None
            rule_condition = None

        # Save result to db
        rule_id = None
        with get_cursor() as cursor:
            if rule:
                cursor.execute("INSERT INTO rule(type, condition, decision) VALUES(%s, %s, %s)"
                               " ON CONFLICT(type, condition) DO UPDATE SET decision=excluded.decision RETURNING id",
                               (rule.value, rule_condition, decision.value))
                rule_id = cursor.fetchone()[0]
                decision = AnnotationDecision.RULE

            if form.ne_type.data:
                # if selection is a candidate than it has ne_type
                cursor.execute("UPDATE annotation SET decision = %s, rule = %s"
                               " WHERE submission = %s and ref_start = %s and ref_end = %s",
                               (decision.value, rule_id, form.submission_id.data, form.ref_start.data, form.ref_end.data))
            else:
                cursor.execute("DELETE FROM annotation"
                               " WHERE submission = %s and %s <= ref_start and ref_end <= %s and ref_type = %s",
                               (form.submission_id.data, form.ref_start.data, form.ref_end.data, ReferenceType.USER.value))
                cursor.execute("INSERT INTO annotation (decision, submission, ref_start, ref_end, ref_type, rule)"
                               " VALUES (%s, %s, %s, %s, %s, %s)",
                               (decision.value, form.submission_id.data, form.ref_start.data, form.ref_end.data,
                                ReferenceType.USER.value, rule_id))
                cursor.execute("UPDATE annotation SET decision = %s"
                               " WHERE submission = %s and %s <= ref_start and ref_end <= %s and ref_type = %s",
                               (AnnotationDecision.NESTED.value, form.submission_id.data, form.ref_start.data, form.ref_end.data,
                                ReferenceType.NAME_ENTRY.value))
            commit()

            if rule:
                # Annotate rest using background task
                from psan.celery import decide
                decide.auto_decide_remaining.delay(form.submission_id.data)

        # Show another tag
        if g.account["type"] != AccountType.ADMIN.value:
            return redirect(url_for(".index"))
        else:
            return redirect(url_for(".show", doc_id=form.submission_id.data, ref_start=form.ref_start.data,
                                    ref_end=form.ref_end.data))
    else:
        return redirect(url_for(".index"))


class RecognizedTagFilter(XMLFilterBase):
    """Transform `ne` tags to `mark` tags. Highlight tag with `id==candidate_id`."""

    def __init__(self, window_start: int, window_end: int, parent):
        super().__init__(parent)

        # View window
        self._window_start = max(0, window_start)
        self._window_end = window_end
        self._in_window = False
        self._real_start = -1
        self._real_end = -1
        # State of parser
        self._token_id = -1
        self._nested_depth = 0
        self._last_sentence = False

    def _startCandidate(self, ref_start, ref_end, entity_type) -> None:
        new_attrs = {"class": "wrapper candidate",
                     "data-ne-type": entity_type,
                     "data-start": str(ref_start),
                     "data-end": str(ref_end),
                     "onClick": f"onTokenIntervalClick(event, {ref_start}, {ref_end})"}
        # Return span element
        self._nested_depth += 1
        super().startElement("span", new_attrs)

    def _endCandidate(self) -> None:
        super().endElement("span")
        self._nested_depth -= 1

    def _startToken(self) -> None:
        new_attrs = {"id": f"token-{self._token_id}",
                     "class": "token",
                     "onClick": f"onTokenClick(event, {self._token_id}, {self._nested_depth})"}
        self._nested_depth += 1
        # Pass updated element
        super().startElement("span", new_attrs)

    def startElement(self, name, attrs):
        if name == "sentence":
            # Parse sentence info
            sentence_start = int(attrs.get("start"))
            sentence_end = int(attrs.get("end"))
            # Show sentences that intersects with window
            if not self._in_window and self._window_start <= sentence_start <= self._window_end:
                self._in_window = True
                self._real_start = sentence_start
            if self._in_window and self._window_end <= sentence_end:
                self._in_window = False
                self._real_end = sentence_end
        elif name == "token":
            self._token_id = int(attrs.get("id"))

        if self._in_window:
            if name == "ne":
                # Get params from XML
                start = int(attrs.get("start"))
                end = int(attrs.get("end"))
                entity_type = attrs.get("type")
                # Transfroms to HTML
                self._startCandidate(start, end, entity_type)
            elif name == "token":
                self._startToken()

    def characters(self, content):
        # Show text only from text window or from last sentence
        if self._in_window or self._last_sentence:
            # Preserve newlines from input file
            fist_line = True
            for line in content.split("\n"):
                super().characters(line)
                if fist_line:
                    fist_line = False
                else:
                    super().startElement("br/", {})

    def endElement(self, name):
        if self._in_window:
            if name == "ne":
                self._endCandidate()
            elif name == "token":
                super().endElement("span")
                self._nested_depth -= 1
                # Check end of reached end of text window
                if self._token_id == self._window_end:
                    while self._nested_depth > 0:
                        super().endElement("span")
                        self._nested_depth -= 1
                    self._in_window = False
                    # Show last sentence in fadeout style (to preserve context)
                    self._last_sentence = True
                    super().startElement("span", {"class": "small fadeout"})
        elif self._last_sentence and name == "sentence":
            super().endElement("span")
            self._last_sentence = False
