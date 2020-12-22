from flask import (Blueprint, flash, g, redirect, render_template, request,
                   session, url_for)
from flask_babel import gettext
from itsdangerous import BadSignature, BadTimeSignature
from werkzeug.exceptions import BadRequest
from werkzeug.security import check_password_hash, generate_password_hash

from psan.auth import login_required
from psan.db import get_db
from psan.model import AccountType, ChangePasswordForm, DeleteAccountForm
from psan.postman import read_reset_token

_ = gettext

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    return render_template("account/index.html", AccountType=AccountType)


@bp.route("/delete", methods=["GET", "POST"])
@login_required
def delete_account():
    delete_form = DeleteAccountForm(request.form)

    if delete_form.validate_on_submit():
        if check_password_hash(g.account["password"], delete_form.password.data):
            db = get_db()
            db.execute("DELETE FROM account WHERE id = %s", (g.account["id"],))
            db.commit()
            session.clear()
            # Show confirmation UI
            flash(_("Account was deleted."), category="message")
            return redirect(url_for("index"))
        else:
            delete_form.password.errors.append(_("Incorrect password."))

    return render_template("account/delete.html", form=delete_form)


@bp.route("/password", methods=["GET", "POST"])
def change_password():
    # Access checks
    token = request.args.get("token")
    if token:  # Token is used for password resetting using email
        try:
            account_id = read_reset_token(token)
        except BadTimeSignature:
            flash(_("Link has expired. Create a new one."), category="error")
            return redirect(url_for("auth.reset"))
        except BadSignature:
            raise BadRequest("Invalid token")
    elif g.account is None:  # Without token the user has to be logged in
        return redirect(url_for("auth.login"))
    else:
        account_id = g.account["id"]

    # Web page
    form = ChangePasswordForm(request.form)

    # Validate form
    if form.validate_on_submit():
        if token or check_password_hash(g.account["password"], form.old_password.data):
            # Update db
            db = get_db()
            db.execute("UPDATE account SET password = %s WHERE id = %s",
                       (generate_password_hash(form.new_password.data), account_id))
            db.commit()
            # Notify user
            flash(_("Password was changed."), category="message")
            return redirect(url_for(".index"))
        else:
            form.old_password.errors.append(_("Incorrect password."))

    return render_template("account/password.html", form=form, token=token is not None)
