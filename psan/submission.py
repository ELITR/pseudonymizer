import gettext
import os

from flask_babel import gettext
from flask.helpers import flash
from werkzeug.utils import secure_filename
from psan.db import get_db
import uuid
import datetime
from flask import current_app, url_for, request, redirect
from werkzeug.datastructures import CombinedMultiDict
from psan.model import AccountType, UploadForm
from flask.blueprints import Blueprint
from psan.auth import login_required
from flask.templating import render_template

_ = gettext

bp = Blueprint("submission", __name__, url_prefix="/submission")


@bp.route("/")
@login_required(role=AccountType.ADMIN)
def index():
    # Load data from db
    db = get_db()
    submissions = db.fetchall("SELECT * FROM submission", None)
    return render_template("submission/index.html", submissions=submissions)


@bp.route("/new", methods=['GET', 'POST'])
@login_required(role=AccountType.ADMIN)
def new():
    form = UploadForm(CombinedMultiDict((request.files, request.form)))
    default_name = datetime.datetime.now().isoformat('T')

    if form.validate_on_submit():
        if not form.file.data and not form.text.data:
            flash(_("File or text input required.", category="error"))
        else:
            # Generete name and uuid
            uid = str(uuid.uuid4())
            if form.name.data:
                name = form.name.data
            else:
                if form.file.data:
                    name = secure_filename(form.file.data.filename)
                else:
                    name = default_name
            # Save uuid to db
            db = get_db()
            db.execute(
                "INSERT INTO submission (uid, name) VALUES (%s, %s)", (uid, name))
            db.commit()
            # Save file
            folder = os.path.join(current_app.config["DATA_FOLDER"], uid)
            os.mkdir(folder)
            if form.file.data:
                form.file.data.save(os.path.join(folder, "input.txt"))
            else:
                with open(os.path.join(folder, "input.txt"), "w") as file:
                    file.write(form.text.data)
            return redirect(url_for(".index"))
    else:
        form.name.render_kw = {"placeholder": default_name}

    return render_template("submission/new.html", form=form)
