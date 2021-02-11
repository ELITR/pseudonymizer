import csv
import gettext
from io import StringIO

from flask import Blueprint, jsonify, make_response, render_template, request

from psan.auth import login_required
from psan.db import commit, get_cursor
from psan.model import AccountType, AnnotationDecision

_ = gettext

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
            rows.append({"id": row["id"], "type": row["type"], "condition": ' '.join(
                row["condition"]), "decision": row["decision"]})
        # Return output
        return jsonify({"total": cursor.rowcount, "totalNotFiltered": not_filtered, "rows": rows})


@bp.route("/remove/<int:rule_id>",  methods=['POST'])
@login_required(role=AccountType.ADMIN)
def remove(rule_id: int):
    with get_cursor() as cursor:
        # Remove already made annotation
        cursor.execute("UPDATE annotation SET rule = NULL, decision = %s WHERE rule = %s",
                       (AnnotationDecision.UNDECIDED.value, rule_id))
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
            cw.writerow((row["type"], ' '.join(row["condition"]), row["decision"]))

    # Prepare output
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output
