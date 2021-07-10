import csv
from io import StringIO

from flask import (Blueprint, g, jsonify, make_response,
                   render_template, request)
from flask_babel import lazy_gettext

from psan.auth import login_required
from psan.db import commit, get_cursor
from psan.model import AccountType

_ = lazy_gettext

bp = Blueprint("label", __name__, url_prefix="/label")


@bp.route("/")
@login_required(role=AccountType.ADMIN)
def index():
    return render_template("label/index.html")


@bp.route("/data")
@login_required()
def data():
    # GET params
    search = request.args.get("search", type=str)

    with get_cursor() as cursor:
        if search:
            cursor.execute("SELECT count(*) FROM label")
            not_filtered = cursor.fetchone()[0]
            cursor.execute("SELECT * FROM label WHERE name LIKE %s OR replacement LIKE %s", (search, search))
        else:
            cursor.execute("SELECT * FROM label")
            not_filtered = cursor.rowcount
        # Prepare data
        rows = []
        for row in cursor:
            # Prepare output
            data = {"id": row["id"], "label": row["name"]}
            if g.account["type"] == AccountType.ADMIN.value:
                data["replacement"] = row["replacement"]
            rows.append(data)
        # Return output
        return jsonify({"total": cursor.rowcount, "totalNotFiltered": not_filtered, "rows": rows})


@bp.route("/new",  methods=['POST'])
@login_required()
def new():
    # Prepare requests
    label = request.form["label"]
    replacement = request.form["replacement"]
    with get_cursor() as cursor:
        # Update value
        cursor.execute("INSERT INTO label (name, replacement) VALUES (%s, %s)", (label, replacement))
        commit()

    # Return OK reply
    return jsonify({"status": "ok"})


@bp.route("/update",  methods=['POST'])
@login_required(role=AccountType.ADMIN)
def update():
    # Prepare requests
    row_id = int(request.form["pk"])
    new_value = request.form["value"]
    with get_cursor() as cursor:
        # Update value
        if request.form["name"] == "label":
            cursor.execute("UPDATE label SET name = %s WHERE id = %s", (new_value, row_id))
        else:
            cursor.execute("UPDATE label SET replacement = %s WHERE id = %s", (new_value, row_id))
        commit()

    # Return OK reply
    return jsonify({"status": "ok"})


@bp.route("/remove/<int:label_id>",  methods=['POST'])
@login_required(role=AccountType.ADMIN)
def remove(label_id: int):
    with get_cursor() as cursor:
        # Remove already made annotation
        cursor.execute("DELETE FROM label WHERE id = %s", (label_id,))
        commit()

    # Return OK reply
    return jsonify({"status": "ok"})


@bp.route('/export')
@login_required(role=AccountType.ADMIN)
def export():
    si = StringIO()
    cw = csv.DictWriter(si, fieldnames=["label", "replacement"])
    cw.writeheader()

    # Prepare data
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM label")
        for row in cursor:
            cw.writerow({"label": row["name"], "replacement": row["replacement"]})

    # Prepare output
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output
