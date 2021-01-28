import datetime
import os
import shutil
import uuid

from flask import current_app, redirect, request, url_for
from flask.blueprints import Blueprint
from flask.helpers import flash
from flask.templating import render_template
from flask_babel import gettext
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.utils import secure_filename

from psan.auth import login_required
from psan.db import commit, get_cursor
from psan.model import (AccountType, RemoveSubmissionForm, SubmissionStatus,
                        UploadForm)

_ = gettext

_INPUT_FILENAME = "01-input.txt"
_RECOGNIZED_FILENAME = "02-recognized.txt"

bp = Blueprint("submission", __name__, url_prefix="/submission")


def get_submission_folder(uid: str) -> str:
    return os.path.join(current_app.config["DATA_FOLDER"], uid)


def get_submission_file(uid: str, status: SubmissionStatus) -> str:
    if status == SubmissionStatus.NEW:
        return os.path.join(current_app.config["DATA_FOLDER"], uid, _INPUT_FILENAME)
    elif status == SubmissionStatus.RECOGNIZED:
        return os.path.join(current_app.config["DATA_FOLDER"], uid, _RECOGNIZED_FILENAME)
    else:
        raise NotImplementedError(f"Unsupported status {status}")


@bp.route("/")
@login_required(role=AccountType.ADMIN)
def index():
    # Load data from db
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT name, uid, status, COUNT(annotation.id) AS candidates, "
            "SUM(CASE WHEN annotation.decision <> 'UNDECIDED' THEN 1 ELSE 0 END) as decided "
            "FROM submission LEFT JOIN annotation ON submission.id=annotation.submission "
            "GROUP BY submission.id ORDER BY submission.id")
        submissions = cursor.fetchall()
    # Remove button
    remove_form = RemoveSubmissionForm(request.form)

    return render_template("submission/index.html", submissions=submissions, remove_form=remove_form,
                           SubmissionStatus=SubmissionStatus)


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
            with get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO submission (uid, name, status) VALUES (%s, %s, %s)",
                    (uid, name, SubmissionStatus.NEW.value))
                commit()
            # Save file
            folder = get_submission_folder(uid)
            os.mkdir(folder)
            if form.file.data:
                form.file.data.save(os.path.join(folder, _INPUT_FILENAME))
            else:
                with open(os.path.join(folder, _INPUT_FILENAME), "w") as file:
                    file.write(form.text.data)
            # Register background task
            from psan.celery import recognize
            recognize.recognize_submission.delay(uid)

            return redirect(url_for(".index"))
    else:
        form.name.render_kw = {"placeholder": default_name}

    return render_template("submission/new.html", form=form)


@bp.route("/remove", methods=["POST"])
@login_required(role=AccountType.ADMIN)
def remove():
    remove_form = RemoveSubmissionForm(request.form)
    if remove_form.validate_on_submit():
        # Remove folder
        shutil.rmtree(os.path.join(
            current_app.config["DATA_FOLDER"], remove_form.uid.data))
        # Remove data from db
        with get_cursor() as cursor:
            cursor.execute("DELETE FROM submission WHERE uid = %s",
                           (remove_form.uid.data,))
            commit()
        # Notify user
        flash(_("Submission removed."))

    return redirect(url_for(".index"))
