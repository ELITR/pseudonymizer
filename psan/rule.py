import gettext

from flask import Blueprint, jsonify, render_template, request

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
