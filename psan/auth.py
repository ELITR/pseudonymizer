import functools
import secrets
import string
from typing import Callable, Optional, Union

from flask import (Blueprint, current_app, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)
from flask_babel import gettext
from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer
from werkzeug.exceptions import BadRequest
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import escape

from psan.db import commit, get_cursor
from psan.model import (AccountRegisterForm, AccountType, LoginForm,
                        PasswordResetForm)
from psan.postman import password_reset

bp = Blueprint("auth", __name__, url_prefix="/auth")
_ = gettext

_AUTH_TOKEN_SALT = "auth"  # nosec
REGISTER_TOKEN_NAME = "register"  # nosec


def _login_required_wrapper(user_fnc: Callable, role: Optional[AccountType], token: Optional[str] = None) -> Callable:
    def wrapper(*args, **kwds):
        # Check token override
        token_data = request.args.get("token", type=str)
        if token_data and token:
            s = URLSafeTimedSerializer(current_app.config["TOKEN_SECRET"], _AUTH_TOKEN_SALT)
            try:
                token_name, = s.loads(token_data, max_age=current_app.config["TOKEN_MAX_AGE"], salt=_AUTH_TOKEN_SALT)
            except BadTimeSignature:
                flash(_("Link has expired. Create a new one."), category="error")
                return redirect(url_for("index"))
            except BadSignature:
                raise BadRequest("Invalid token")
            if token_name != token:
                raise BadRequest("Invalid token")
        elif g.account is None:
            flash(_("Log in needed"), category="info")
            return redirect(url_for("auth.login"))
        elif role and g.account["type"] != role.value:
            flash(_("Insufficient permission"), category="error")
            return redirect(url_for("account.index"))
        # Show required page if everything pass
        return user_fnc(*args, **kwds)
    return wrapper


def login_required(role: Union[Optional[AccountType], Callable] = None, token: Optional[str] = None):
    """View decorator that redirects anonymous users to the login page."""

    # Make it work for @f
    if callable(role):
        user_fnc, role = role, None
        return functools.update_wrapper(_login_required_wrapper(user_fnc, role, token), user_fnc)
    else:
        # Make it work for @f(role)
        def decorating_function(user_fnc):
            return functools.update_wrapper(_login_required_wrapper(user_fnc, role, token), user_fnc)

        return decorating_function


def generate_auth_token(token_name: str) -> str:
    """Generates token that can override login_required annotation"""
    s = URLSafeTimedSerializer(current_app.config["TOKEN_SECRET"], _AUTH_TOKEN_SALT)
    return s.dumps((token_name,))


@bp.before_app_request
def load_logged_in_account():
    """If a account id is stored in the session, load the account object from
    the database into ``g.account``."""
    account_id = session.get("account_id")

    g.account = None
    if account_id:
        with get_cursor() as cursor:
            cursor.execute("SELECT * FROM account WHERE id = %s", (account_id,))
            g.account = cursor.fetchone()


def is_email_unique(cursor, email: str) -> bool:
    cursor.execute("SELECT id FROM account WHERE email = %s", (email,))
    if cursor.fetchone() is not None:
        flash(_("E-mail %(value)s is already taken.", value=escape(email)),
              category="error")
        return False
    else:
        return True


@bp.route("/register", methods=("GET", "POST"))
@login_required(role=AccountType.ADMIN, token=REGISTER_TOKEN_NAME)
def register():
    """Register a new account.
    Validates that the email is not already taken. Handles password for security.
    """

    form = AccountRegisterForm(request.form)
    if request.method == "POST":
        # Prepare cursor for db access
        cursor = get_cursor()
        # Check form data
        if not form.validate():
            flash(_("Form content is not valid."), category="error")
        elif is_email_unique(cursor, form.email.data):
            cursor.execute(
                "INSERT INTO account (full_name, type, window_size, email, password) "
                "VALUES (%s, %s, %s, %s, %s)",
                (form.full_name.data, form.type.data, form.window_size.data, form.email.data,
                 generate_password_hash(form.password.data)),
            )
            commit()
            cursor.close()
            # Notify user
            flash(_("Registration was successful."), category="message")

            # Redirect to correct page
            if g.account:
                return redirect(url_for("account.index"))
            else:
                return redirect(url_for("auth.login"))
        else:
            cursor.close()
            form.email.errors.append(_("Value is already taken."))
    else:
        form.password.data = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Log in a registered account by adding the account id to the session."""
    form = LoginForm(request.form)
    if request.method == "POST":
        error = False

        if not form.validate():
            flash(_("Form content is not valid."), category="error")
        else:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM account WHERE email = %s", (form.email.data,))
                account = cursor.fetchone()

            if account is None:
                flash(_("Incorrect e-mail."), category="error")
                error = True
            elif not check_password_hash(account["password"], form.password.data):
                flash(_("Incorrect password."), category="error")
                error = True

            if error is False:
                # store the account id in a new session and return to the index
                session.clear()
                session["account_id"] = account["id"]
                return redirect(url_for("account.index"))

    return render_template("auth/login.html", form=form)


@bp.route("/user")
@login_required(role=AccountType.ADMIN)
def users():
    # Prepare data
    with get_cursor() as cursor:
        cursor.execute("SELECT id, full_name, email, type, window_size FROM account")
        # Prepare data
        rows = []
        for row in cursor:
            rows.append({"id": row["id"], "name": f"{row['full_name']} ({row['email']})", "type": row["type"],
                         "window_size": row["window_size"]})
    # Return output
    return jsonify({"total": cursor.rowcount, "totalNotFiltered": cursor.rowcount, "rows": rows})


@bp.route("/user/remove/<int:user_id>",  methods=['POST'])
@login_required(role=AccountType.ADMIN)
def user_remove(user_id: int):
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM account WHERE id = %s", (user_id,))
        commit()

    # Return OK reply
    return jsonify({"stutus": "ok"})


@bp.route("/logout")
def logout():
    """Clear the current session, including the stored account id."""
    session.clear()
    return redirect(url_for("index"))


@bp.route("/reset", methods=("GET", "POST"))
def reset():
    """Send e-mail with link to reset password."""
    form = PasswordResetForm(request.form)
    if request.method == "POST":
        if not form.validate():
            flash(_("Form content is not valid."), category="error")
        else:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM account WHERE email = %s", (form.email.data,))
                account = cursor.fetchone()

            if account is None:
                flash(_("Unknown e-mail."), category="error")
            else:
                password_reset(request.remote_addr, account["id"])
                flash(
                    _("Login and password reset link was sent to your e-mail address."), category="message")
                return redirect(url_for("index"))

    return render_template("auth/reset.html", form=form)
