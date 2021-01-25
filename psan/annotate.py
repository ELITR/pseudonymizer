import re
from io import StringIO
from typing import Hashable, List
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
                        ReferenceType, RuleType, SubmissionStatus)
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
    doc_id = request.args.get("doc_id", type=int)
    ref_start = request.args.get("ref_start", type=int)
    ref_end = request.args.get("ref_end", type=int)
    return show_candidate(doc_id, ref_start, ref_end)


def show_candidate(submission_id: int, ref_start: int, ref_end: int):
    # Find UID
    with get_cursor() as cursor:
        cursor.execute("SELECT uid FROM submission WHERE id = %s", (submission_id,))
        submission_uid = cursor.fetchone()["uid"]

    # Find line with token ID == ref_start
    token_line = None
    with open(get_submission_file(submission_uid, SubmissionStatus.RECOGNIZED), "r") as input:
        pattern = re.compile(f"<token[^<>]+id=\"{ref_start}\"")
        for line in input:
            if pattern.search(line):
                token_line = line
                break
    # Check if any token was found
    if not token_line:
        raise InternalServerError(
            f"Cannot find token id {ref_start} from submission {submission_uid}")

    # Transform line for UI
    output = StringIO()
    generator = XMLGenerator(output)
    filter = RecognizedTagFilter(submission_id, ref_start, ref_end, make_parser())
    filter.setContentHandler(generator)
    # Line has to be surrounded with XML tags
    sax.parseString(token_line, filter)

    # Show correct NE type string
    ne_type_code = filter.entity_type
    if filter.entity_type in NE_CODES:
        ne_type_str = NE_CODES[ne_type_code]
    else:
        ne_type_str = ne_type_code if ne_type_code else ""
    tokens_str = " ".join(filter.highlight_tokens)

    form = AnnotateForm(request.form)

    return render_template("annotate/index.html", context_html=output.getvalue(), ne_type_str=ne_type_str,
                           ne_type_code=ne_type_code, token_str=tokens_str, form=form, submission_id=submission_id,
                           ref_start=ref_start, ref_end=ref_end)


@bp.route("/set", methods=['POST'])
@login_required()
def set():
    form = AnnotateForm(request.form)
    if form.validate():
        # Process decision
        if form.ctx_public.data or form.lemma_public.data or form.ne_type_public.data:
            decision = AnnotationDecision.PUBLIC
        elif form.ctx_secret.data or form.lemma_secret.data or form.ne_type_secret.data:
            decision = AnnotationDecision.SECRET
        # Process decision condition
        if form.lemma_public.data or form.lemma_secret.data:
            rule = RuleType.LEMMA
            rule_condition = "LEMMAS"  # TODO
        elif form.ne_type_public.data or form.ne_type_secret.data:
            rule = RuleType.NE_TYPE
            rule_condition = form.ne_type.data
        else:
            rule = None

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
                cursor.execute("UPDATE annotation SET decision = %s, rule = %s WHERE submission = %s and ref_start = %s and ref_end = %s",
                               (decision.value, rule_id, form.submission_id.data, form.ref_start.data, form.ref_end.data))

            else:
                cursor.execute("DELETE FROM annotation WHERE submission = %s and %s <= ref_start and ref_end <= %s and ref_type = %s",
                               (form.submission_id.data, form.ref_start.data, form.ref_end.data, ReferenceType.USER.value))
                cursor.execute("INSERT INTO annotation (decision, submission, ref_start, ref_end, ref_type, rule) VALUES (%s, %s, %s, %s, %s, %s)",
                               (decision.value, form.submission_id.data, form.ref_start.data, form.ref_end.data, ReferenceType.USER.value, rule_id))
                cursor.execute("UPDATE annotation SET decision = %s WHERE submission = %s and %s <= ref_start and ref_end <= %s and ref_type = %s",
                               (AnnotationDecision.NESTED.value, form.submission_id.data, form.ref_start.data, form.ref_end.data, ReferenceType.NAME_ENTRY.value))
            commit()

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

    def __init__(self, doc_id: int, highlight_start: int, highlight_end: int, parent=None):
        super().__init__(parent)

        # Tag to highlight
        self._window_start = highlight_start - 200
        self._window_end = highlight_end + 200
        self._annotations = RecognizedTagFilter._get_decisions(doc_id, self._window_start, self._window_end)
        self._highlight_start = highlight_start
        self._highlight_end = highlight_end
        self.highlight_tokens = []
        self._user_cadidate_end = -1
        self._token_id = -1
        self._nested_depth = 0
        self.entity_type = None

    @ staticmethod
    def _get_decisions(submission_id: int, window_start, window_end) -> List[Hashable]:
        """Returns decision in defined interval. Returns `decision[ref_start - window_start][len] = decision_str´ """
        decisions = [{} for _ in range(window_end - window_start)]
        with get_cursor() as cursor:
            cursor.execute("SELECT ref_start, ref_end, COALESCE(rule.decision::text, annotation.decision::text) as decision FROM annotation"
                           " LEFT JOIN rule ON annotation.rule = rule.id"
                           " WHERE submission = %s and (ref_start > %s and ref_end < %s) or (ref_end > %s and ref_start < %s)"
                           " ORDER BY ref_start",
                           (submission_id, window_start, window_end, window_start, window_end))
            for row in cursor:
                decisions[row["ref_start"] - window_start][row["ref_end"] - row["ref_start"]] = row["decision"]
        return decisions

    def _startCandidate(self, ref_start, ref_end, is_highlighted) -> None:
        annotation = self._annotations[ref_start - self._window_start].get(ref_end-ref_start)
        if annotation == AnnotationDecision.PUBLIC.value:
            new_attrs = {"class": "candidate candidate-public"}
        elif annotation == AnnotationDecision.SECRET.value:
            new_attrs = {"class": "candidate candidate-secret"}
        else:
            new_attrs = {"class": "candidate"}
        # Check highlight
        if is_highlighted:
            new_attrs["class"] += " highlight"
        # Mouse events
        new_attrs["onClick"] = f"onTokenIntervalClick(event, {ref_start}, {ref_end})"
        # Return span element
        self._nested_depth += 1
        super().startElement("span", new_attrs)

    def _endCandidate(self) -> None:
        super().endElement("span")
        self._nested_depth -= 1

    def _startToken(self) -> None:
        new_attrs = {"class": "token"}
        # Check for user highlight
        if self._token_id == self._highlight_start:
            new_attrs["class"] += " highlight"
            assert self._user_cadidate_end == -1  # nosec
            self._user_cadidate_end = self._highlight_end
        else:
            # Check for known decision
            for length, decision in self._annotations[self._token_id - self._window_start].items():
                if decision == AnnotationDecision.PUBLIC.value:
                    new_attrs = {"class": "token candidate-public"}
                    self._user_cadidate_end = self._token_id + length
                    break
                elif decision == AnnotationDecision.SECRET.value:
                    new_attrs = {"class": "token candidate-secret"}
                    self._user_cadidate_end = self._token_id + length
                    break
        # If we have to transform token to candidate
        if self._user_cadidate_end != -1:
            new_attrs["onClick"] = f"onTokenIntervalClick(event, {self._token_id},  {self._user_cadidate_end})"
            self._nested_depth += 1
        else:
            new_attrs["onClick"] = f"onTokenClick(event, {self._token_id})"
        # Pass updated element
        super().startElement("span", new_attrs)

    def startElement(self, name, attrs):
        if name == "ne":
            # Get params from XML
            start = int(attrs.get("start"))
            end = int(attrs.get("end"))
            highlighted = self._highlight_start <= start and end <= self._highlight_end
            # Get name entity type
            if self._highlight_start == start and end == self._highlight_end:
                self.entity_type = attrs.get("type")
            # Add another token tag if candidate starts hightlight interval
            if self._nested_depth == 0 and start == self._highlight_start and end < self._highlight_end:
                self._token_id = start
                self._startToken()
            # Transfroms to HTML
            self._startCandidate(start, end, highlighted)
        elif name == "token":
            self._token_id = int(attrs.get("id"))
            # Check if token isn't nested insede another annotation
            if (self._nested_depth == 0):
                self._startToken()
        elif name == "sentence":
            pass
        else:
            super().startElement(name, attrs)

    def characters(self, content):
        # Save highlighted tokens
        if self._highlight_start <= self._token_id <= self._highlight_end:
            self.highlight_tokens.append(content)

        return super().characters(content)

    def endElement(self, name):
        if name == "ne":
            self._endCandidate()
        elif name == "token":
            if self._nested_depth == 0:
                super().endElement("span")
            elif self._user_cadidate_end == self._token_id:
                super().endElement("span")
                self._nested_depth -= 1
                self._user_cadidate_end = -1
        elif name == "sentence":
            pass
        else:
            super().endElement(name)
