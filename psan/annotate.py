import json
from io import StringIO
from xml import sax  # nosec
from xml.sax import make_parser  # nosec
from xml.sax.saxutils import XMLFilterBase, XMLGenerator  # nosec

from celery_once import AlreadyQueued
from flask import (Blueprint, Response, current_app, g, jsonify, make_response,
                   render_template, request, session)
from flask_babel import gettext
from werkzeug.exceptions import BadRequest

from psan.auth import login_required
from psan.db import commit, get_cursor
from psan.model import AccountType, SubmissionStatus
from psan.submission import get_submission_file
from psan.tool.controller import Controller
from psan.tool.model import AnnotationDecision, Interval, RuleType

_ = gettext

bp = Blueprint("annotate", __name__, url_prefix="/annotate")


def _check_permissinns(start: int, end: int, doc_id: int) -> None:
    # Check params presence
    if start is None or end is None or doc_id is None:
        raise BadRequest("Missing required parameters ref_start, ref_end or document_id")
    # Check window permission
    is_admin = (g.account["type"] == AccountType.ADMIN.value)
    if (start < session["permitted_win_start"] or session["permitted_win_end"] < end
            or session["permitted_doc_id"] != doc_id) and not is_admin:
        raise BadRequest("Insufficient permissions for this window")


def _call_re_annotate(doc_id: int) -> None:
    # Annotate rest using background task
    from psan.celery import re_annotate
    re_annotate.re_annotate.delay(doc_id)
    # Annotate other documents after 120
    try:
        re_annotate.re_annotate_all.apply_async((doc_id,), countdown=120)
    except AlreadyQueued:
        pass


@bp.route("/")
@login_required()
def index():
    # Find longest submission from db
    with get_cursor() as cursor:
        min_confidence = current_app.config["RULE_AUTOAPPLY_CONFIDENCE"]
        # Faster method
        cursor.execute("SELECT submission.id as id FROM submission "
                       " WHERE status = %s AND EXISTS ( SELECT 1 FROM"
                       " annotation WHERE submission.id=annotation.submission and"
                       " (token_level IS NULL and ABS(rule_level) < %s))"
                       " ORDER BY random() LIMIT 1",
                       (SubmissionStatus.PRE_ANNOTATED.value, min_confidence))
        document = cursor.fetchone()
        if not document:
            # Much slower method for missing labels
            cursor.execute("SELECT s.id as id FROM submission s "
                           " WHERE s.status = %s AND EXISTS ("
                           " SELECT 1 FROM annotation a"
                           " LEFT JOIN (annotation_rule ar "
                           " INNER JOIN rule r ON r.id = ar.rule AND r.label IS NOT NULL AND r.confidence < 0)"
                           " ON ar.annotation = a.id"
                           " WHERE a.submission = s.id and ((token_level IS NULL AND ABS(rule_level) < %s)"  # not decided
                           " OR ((token_level = %s OR (token_level IS NULL AND rule_level < %s))"  # or (secret
                           " and COALESCE(a.label, r.label) IS NULL)))"
                           " ORDER BY random() LIMIT 1",
                           (SubmissionStatus.PRE_ANNOTATED.value, min_confidence, AnnotationDecision.SECRET.value,
                            min_confidence))
            document = cursor.fetchone()
        if document:
            # Show first candadate of submission
            cursor.execute("SELECT submission, ref_start, ref_end"
                           " FROM annotation a"
                           " LEFT JOIN (annotation_rule ar "
                           " INNER JOIN rule r ON r.id = ar.rule AND r.label IS NOT NULL AND r.confidence < 0)"
                           " ON ar.annotation = a.id"
                           " WHERE submission=%s and ((token_level IS NULL AND ABS(rule_level) < %s)"  # not decided
                           " OR ((token_level = %s OR (token_level IS NULL AND rule_level < %s))"  # or (secret
                           " and COALESCE(a.label, r.label) IS NULL))"  # and missing label)
                           " ORDER BY ref_start"
                           " LIMIT 1",
                           (document["id"], min_confidence, AnnotationDecision.SECRET.value, min_confidence))
            candidate = cursor.fetchone()
            return show_candidate(candidate["submission"], candidate["ref_start"], candidate["ref_end"])
        else:
            return render_template("annotate/empty.html")


@ bp.route("/show")
@ login_required(role=AccountType.ADMIN)
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
    win_start = max(ref_start - g.account["window_size"], 0)
    win_end = ref_start + g.account["window_size"]
    # Add permission
    session["permitted_doc_id"] = submission_id
    session["permitted_win_start"] = win_start
    session["permitted_win_end"] = win_end

    is_admin = (g.account["type"] == AccountType.ADMIN.value)
    return render_template("annotate/index.html", submission_id=submission_id,  win_start=win_start, win_end=win_end,
                           highlight_start=ref_start, highlight_end=ref_end, is_admin=is_admin)


@ bp.route("/window")
@ login_required()
def window():
    # Parse input params
    submission_id = request.args.get("doc_id", type=int)
    start = request.args.get("start", type=int)
    end = request.args.get("end", type=int)
    _check_permissinns(start, end, submission_id)

    # Don't generate text window each time (use cache instead)
    if request.if_none_match and f"{submission_id}-{start}-{end}" in request.if_none_match:
        return Response(status=304)  # Return HTTP 304 (Not modified)
    else:
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
        filter.appendNeTypes()
        # Prepare response
        response = make_response(output.getvalue())
        # Enable browser cache
        response.set_etag(f"{submission_id}-{start}-{end}")
        return response


@ bp.route("/decisions")
@ login_required()
def decisions():
    # Parse input params
    submission_id = request.args.get("doc_id", type=int)
    window_start = request.args.get("start", type=int)
    window_end = request.args.get("end", type=int)
    _check_permissinns(window_start, window_end, submission_id)

    min_confidence = current_app.config["RULE_AUTOAPPLY_CONFIDENCE"]

    # Returns decision in defined interval
    decisions = []
    with get_cursor() as cursor:
        ctl = Controller(cursor, submission_id, g.account["id"])
        decisions = ctl.get_decisions(Interval(window_start, window_end), min_confidence)
    return jsonify(decisions)


@ bp.route("/detail")
@ login_required()
def detail():
    # Parse input params
    submission_id = request.args.get("doc_id", type=int)
    start = request.args.get("start", type=int)
    end = request.args.get("end", type=int)
    _check_permissinns(start, end, submission_id)

    # Returns decision in defined interval
    with get_cursor() as cursor:
        # Annotation info
        cursor.execute("SELECT a.id, token_level, account.full_name AS annotation_author"
                       " FROM annotation a"
                       " LEFT JOIN account ON a.author = account.id"
                       " WHERE submission = %s and ref_start = %s and ref_end = %s",
                       (submission_id, start, end))
        row = cursor.fetchone()
        annotation_id = row["id"]
        response = {"token_author": row["annotation_author"], "token_level": row["token_level"]}
        # Rules info
        rules = []
        cursor.execute("SELECT r.type, condition, confidence, account.full_name AS rule_author"
                       " FROM rule r"
                       " JOIN annotation_rule ar ON r.id = ar.rule AND ar.annotation = %s"
                       " LEFT JOIN account ON r.author=account.id"
                       " ORDER BY confidence ASC",
                       (annotation_id, ))
        for row in cursor:
            rules.append({"type": row["type"], "condition": row["condition"], "confidence": row["confidence"],
                          "author": row["rule_author"]})
        response["rules"] = rules

        return jsonify(response)


@ bp.route("/decision", methods=['POST'])
@ login_required()
def decision():
    # Window detail
    doc_id = request.form.get("doc_id", type=int)
    ref_start = request.form.get("ref_start", type=int)
    ref_end = request.form.get("ref_end", type=int)
    _check_permissinns(ref_start, ref_end, doc_id)

    # Process decision
    if request.form["decision"] == "PUBLIC":
        decision = AnnotationDecision.PUBLIC
    else:
        decision = AnnotationDecision.SECRET

    # Rule type
    rule_type = None
    condition = None
    if request.form["kind"] == "NE_TYPE":
        rule_type = RuleType.NE_TYPE
        condition = [request.form["ne_type"]]
    elif request.form["kind"] == "WORD_TYPE":
        rule_type = RuleType.WORD_TYPE
        condition = json.loads(request.form["tokens"])

    # Save result to db
    interval = Interval(ref_start, ref_end)
    rule_confidence = 1 if decision == AnnotationDecision.PUBLIC else -1

    with get_cursor() as cursor:
        ctl = Controller(cursor, doc_id, g.account["id"])
        # Decision connected with rules
        if rule_type:
            rule = ctl.set_rule(rule_type, condition, rule_confidence)
        # Token level annotation
        annotation_id = ctl.token_annotation(interval, decision)
        # Improved search for candidates
        candidate = None
        if rule_type != RuleType.NE_TYPE:
            if decision == AnnotationDecision.SECRET:
                candidate = ctl.add_candidate_rule(json.loads(request.form["tokens"]), annotation_id)
            else:
                ctl.drop_candidate_rule(annotation_id)
        # (Pre) connect rule to annotation
        if rule_type:
            ctl.connect(annotation_id, rule)

        # Commit changes to database
        commit()

    if rule_type or candidate:
        # Annotate rest using background task
        _call_re_annotate(doc_id)

    # Send OK reply
    return jsonify({"status": "ok"})


@ bp.route("/label", methods=['POST'])
@ login_required()
def label():
    # Window detail
    doc_id = request.form.get("doc_id", type=int)
    ref_start = request.form.get("ref_start", type=int)
    ref_end = request.form.get("ref_end", type=int)
    types = json.loads(request.form.get("types", type=str))
    label = request.form.get("label", type=int)
    as_rule = request.form.get("rule", type=bool)

    _check_permissinns(ref_start, ref_end, doc_id)

    interval = Interval(ref_start, ref_end)
    with get_cursor() as cursor:
        ctl = Controller(cursor, doc_id, g.account["id"])
        # Token level annotation
        annotation_id = ctl.token_annotation(interval, AnnotationDecision.SECRET)
        # Update label
        ctl.set_label(interval, label)
        # Improved search for candidates
        candidate = ctl.add_candidate_rule(types, annotation_id)
        # Set rule label
        if as_rule:
            ctl.set_rule_label(types, label)
        commit()
        # Annotate rest of file using new candidate
        if candidate:
            _call_re_annotate()

    return jsonify({"status": "ok"})


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
        self._ne_types = {}
        # State of parser
        self._token_id = -1
        self._nested_depth = 0
        self._last_sentence = False

    def _startToken(self) -> None:
        new_attrs = {"id": f"token-{self._token_id}",
                     "class": "token",
                     "onClick": f"onTokenClick(event, {self._token_id})"}
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
                # Register ne_type
                self._ne_types[f"{start}-{end}"] = entity_type

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
            # Parse tokens ignore "ne" tags
            if name == "token":
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

    def appendNeTypes(self) -> None:
        super().startElement("script", {})
        super().characters(f"var window_ne_types = {json.JSONEncoder().encode(self._ne_types)};")
        super().endElement("script")
