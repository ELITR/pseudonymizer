import gettext

from flask import Blueprint, jsonify, render_template

from psan.auth import login_required
from psan.db import get_cursor

_ = gettext

bp = Blueprint("rule", __name__, url_prefix="/rule")


@bp.route("/")
@login_required()
def index():
    return render_template("rule/index.html")


@bp.route("/data")
@login_required()
def data():
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM rule")
        # Prepare data
        rows = []
        for row in cursor:
            rows.append({"id": row["id"], "type": row["type"], "condition": ' '.join(
                row["condition"]), "decision": row["decision"]})
        # Return output
        return jsonify({"total": cursor.rowcount, "totalNotFiltered": cursor.rowcount, "rows": rows})
