from flask import Blueprint, render_template
from flask_babel import gettext

from psan.auth import login_required

_ = gettext

bp = Blueprint("annotate", __name__, url_prefix="/annotate")


@bp.route("/")
@login_required()
def index():
    return render_template("annotate/index.html")
