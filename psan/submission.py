from psan.model import AccountType
from flask.blueprints import Blueprint
from psan.auth import login_required
from flask.templating import render_template


bp = Blueprint("submission", __name__, url_prefix="/submission")


@bp.route("/")
@login_required(role=AccountType.ADMIN)
def index():
    return render_template("request/index.html")
