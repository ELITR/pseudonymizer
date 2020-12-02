import email.message
import smtplib
from typing import Tuple

from flask import current_app, url_for
from flask_babel import gettext
from itsdangerous import URLSafeTimedSerializer

from psan import db

_ = gettext

email_verify_text = _("""Hi,

We received your request to use {email} in pseudo-anonymize tool. To confirm your address you have to visit the link below:

{verify_url}

The link is valid for {max_age} minutes. You can manage your settings on a web tool at {server_root}.

Kind regards,
Automat of PsAn tool
""")

reset_password_text = _("""Hi,

We received request from {ip} to reset password. To log in use e-mail `{email}`. To reset your password visit the link below:

{reset_url}

The link is valid for {max_age} minutes. You can manage your settings on a web tool at {server_root}.

Kind regards,
Automat of PsAn tool
""")


def verify_email(account_id: int, new_email: str) -> None:
    # Account info
    verify_url = url_for("account.confirm", token=build_token((account_id, new_email), "email"),
                         _external=True)
    # Email message
    msg = email.message.EmailMessage()
    msg['Subject'] = _("E-mail confirmation for PSAN")
    msg['From'] = current_app.config["TOKEN_FROM_EMAIL"]
    msg['To'] = new_email
    body = email_verify_text.format(
        email=new_email,
        verify_url=verify_url,
        max_age=current_app.config["TOKEN_MAX_AGE"] / 60,
        server_root=url_for("index", _external=True)
    )
    msg.set_content(body, cte='quoted-printable')

    smtp = smtplib.SMTP(current_app.config["TOKEN_SMTP_HOST"])
    smtp.send_message(msg)
    smtp.quit()


def password_reset(client_ip: str, account_id: int) -> None:
    # Account info
    account = db.get_db().fetchone("SELECT * FROM account WHERE id = %s", (account_id,))
    reset_url = url_for("account.change_password", token=build_token(
        (account_id,), "reset"), _external=True)
    # Email message
    msg = email.message.EmailMessage()
    msg['Subject'] = _("Password reset for PSAN")
    msg['From'] = current_app.config["TOKEN_FROM_EMAIL"]
    msg['To'] = account["email"]
    body = reset_password_text.format(
        email=account["email"],
        ip=client_ip,
        reset_url=reset_url,
        max_age=current_app.config["TOKEN_MAX_AGE"] / 60,
        server_root=url_for("index", _external=True)
    )
    msg.set_content(body, cte='quoted-printable')

    smtp = smtplib.SMTP(current_app.config["TOKEN_SMTP_HOST"])
    smtp.send_message(msg)
    smtp.quit()


def build_token(data: Tuple, salt: str) -> str:
    s = URLSafeTimedSerializer(current_app.config["TOKEN_SECRET"], salt)
    return s.dumps(data)


def read_token(token: str, salt: str) -> Tuple:
    s = URLSafeTimedSerializer(current_app.config["TOKEN_SECRET"], salt)
    return s.loads(token, max_age=current_app.config["TOKEN_MAX_AGE"], salt=salt)


def read_email_token(token: str) -> Tuple[int, str]:
    """
    Validates token and returns account_id and e-mail
    """
    return read_token(token, "email")


def read_reset_token(token: str) -> int:
    """
    Validates token and returns account_id
    """
    account_id, = read_token(token, "reset")
    return account_id
