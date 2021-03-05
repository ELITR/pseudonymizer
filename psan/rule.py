import csv
from io import StringIO, TextIOWrapper

from flask import (Blueprint, flash, jsonify, make_response, redirect,
                   render_template, request, url_for)
from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from psycopg2.errors import DataError
from wtforms import SubmitField
from wtforms.fields.simple import TextAreaField

from psan.auth import login_required
from psan.db import commit, get_cursor
from psan.model import AccountType, AnnotationDecision, RuleType

_ = lazy_gettext

bp = Blueprint("rule", __name__, url_prefix="/rule")


@bp.route("/")
@login_required(role=AccountType.ADMIN)
def index():
    return render_template("rule/index.html")


@bp.route("/data")
@login_required(role=AccountType.ADMIN)
def data():
    # GET params
    search = request.args.get("search", type=str)

    with get_cursor() as cursor:
        if search:
            cursor.execute("SELECT count(*) FROM rule")
            not_filtered = cursor.fetchone()[0]
            cursor.execute("SELECT * FROM rule WHERE array_to_string(condition, ' ') LIKE %s", (search,))
        else:
            cursor.execute("SELECT * FROM rule")
            not_filtered = cursor.rowcount
        # Prepare data
        rows = []
        for row in cursor:
            # Prepare condition string
            if row["type"] == RuleType.NE_TYPE.value:
                condition_str = "NE_TYPE:" + ' '.join(row["condition"])
            else:
                condition_str = ' '.join(row["condition"])
            # Prepare output
            rows.append({"id": row["id"], "type": row["type"], "condition": condition_str, "decision": row["decision"]})
        # Return output
        return jsonify({"total": cursor.rowcount, "totalNotFiltered": not_filtered, "rows": rows})


@bp.route("/remove/<int:rule_id>",  methods=['POST'])
@login_required(role=AccountType.ADMIN)
def remove(rule_id: int):
    with get_cursor() as cursor:
        # Find rule type
        cursor.execute("SELECT type FROM rule WHERE id = %s", (rule_id,))
        rule_type = cursor.fetchone()["type"]
        # Remove already made annotation
        if rule_type == RuleType.NE_TYPE.value:
            cursor.execute("UPDATE annotation SET rule = NULL, decision = %s WHERE rule = %s",
                           (AnnotationDecision.UNDECIDED.value, rule_id))
        else:
            cursor.execute("DELETE FROM annotation WHERE rule = %s", (rule_id,))
        # Remove rule
        cursor.execute("DELETE FROM rule WHERE id = %s", (rule_id,))
        commit()

    # Return OK reply
    return jsonify({"stutus": "ok"})


@bp.route('/export')
@login_required(role=AccountType.ADMIN)
def export():
    si = StringIO()
    cw = csv.writer(si)

    # Prepare data
    with get_cursor() as cursor:
        cursor.execute("SELECT type, condition, decision FROM rule")
        for row in cursor:
            cw.writerow((row["type"], '='.join(row["condition"]), row["decision"]))

    # Prepare output
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output


class UploadForm(FlaskForm):
    text = TextAreaField(_("Text rules"))
    file = FileField(_("CSV file"), validators=[
                     FileAllowed(["csv", "txt"], _("*.csv files only"))])
    submit = SubmitField(_("Upload"))


@bp.route('/import', methods=["GET", "POST"])
@login_required(role=AccountType.ADMIN)
def upload():
    form = UploadForm()
    if form.validate_on_submit():
        if not form.file.data and not form.text.data:
            flash(_("File or text input required."), category="error")
        else:
            # Load input
            if form.file.data:
                csv_input = csv.reader(TextIOWrapper(form.file.data, "UTF8"))
            else:
                csv_input = csv.reader(form.text.data.splitlines())
            # Import input
            line_num = 0
            with get_cursor() as cursor:
                for row in csv_input:
                    # Line numbering
                    line_num += 1
                    if len(row) == 0:
                        continue
                    # Try to import to db
                    try:
                        cursor.execute("INSERT INTO rule (type, condition, decision) VALUES(%s, %s, %s)"
                                       " ON CONFLICT (type, condition) DO UPDATE SET decision = EXCLUDED.decision",
                                       (row[0], row[1].split('='), row[2]))
                    except (IndexError, DataError):
                        flash(_("Illegal format on line %(line_num)s.", line_num=line_num), category="error")
                        return render_template("rule/import.html", form=form)
                commit()

            flash(_("%(num)s rules imported", num=csv_input.line_num), category="message")
            return redirect(url_for(".index"))

    # Prepare output
    return render_template("rule/import.html", form=form)
