from enum import Enum

from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (PasswordField, SelectField, StringField, SubmitField,
                     validators)
from wtforms.fields.html5 import EmailField
from wtforms.fields.simple import HiddenField, TextAreaField

_ = lazy_gettext


class AccountType(Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class SubmissionStatus(Enum):
    NEW = "NEW"
    RECOGNIZED = "RECOGNIZED"
    ANNOTATED = "ANNOTATED"
    DONE = "DONE"


class AnnotationDecision(Enum):
    SECRET = "SECRET"  # nosec
    PUBLIC = "PUBLIC"
    RULE = "RULE"
    NESTED = "NESTED"
    UNDECIDED = "UNDECIDED"


class ReferenceType(Enum):
    NAME_ENTRY = "NAME_ENTRY"
    USER = "USER"


class RuleType(Enum):
    WORD_TYPE = "WORD_TYPE"
    LEMMA = "LEMMA"
    NE_TYPE = "NE_TYPE"


def strip_whitespace(text: str):
    return text.strip()


email_validators = [validators.DataRequired(),
                    validators.length(max=255),
                    validators.regexp(r".+@.+", message=_("E-mail must contains @ inside text"))]


class AccountRegisterForm(FlaskForm):
    full_name = StringField(_("Full name"), [validators.DataRequired(), validators.length(3, 70)],
                            render_kw={"autofocus": True}, filters=[strip_whitespace])
    type = SelectField(_("Account type"),
                       choices=[(AccountType.USER.value, _("User")),
                                (AccountType.ADMIN.value, _("Admin"))])
    email = EmailField(_("E-mail address"),
                       validators=email_validators,
                       filters=[strip_whitespace])
    password = StringField(_("Password"),
                           description=_("At least 8 characters long"),
                           validators=[validators.DataRequired(),
                                       validators.length(8)],
                           filters=[strip_whitespace])
    submit = SubmitField(_("Register"))


class LoginForm(FlaskForm):
    email = StringField(
        _("E-mail address"), [validators.DataRequired()], render_kw={"autofocus": True})
    password = PasswordField(_("Password"), [validators.DataRequired()])
    submit = SubmitField(_("Log in"))


class PasswordResetForm(FlaskForm):
    email = StringField(_("E-mail address"),
                        filters=[strip_whitespace],
                        render_kw={"autofocus": True})
    submit = SubmitField(_("Submit"))


class DeleteAccountForm(FlaskForm):
    password = PasswordField(_("Password"), [validators.DataRequired()])
    submit = SubmitField(_("Delete account"))


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField(
        _("Old password"), [validators.DataRequired()])
    new_password = PasswordField(_("New password"),
                                 description=_("At least 8 characters long"),
                                 validators=[validators.DataRequired(),
                                             validators.length(8),
                                             validators.EqualTo("confirm", message=_("Passwords must match"))])
    confirm = PasswordField(_("Repeat new password"), [
                            validators.DataRequired()])
    submit = SubmitField(_("Change password"))


class UploadForm(FlaskForm):
    name = StringField(_("Submission name"))
    text = TextAreaField(_("Text submission"))
    file = FileField(_("Text file submission"), validators=[
                     FileAllowed(["txt"], _("*.txt files only"))])
    submit = SubmitField(_("Upload"))


class RemoveSubmissionForm(FlaskForm):
    uid = HiddenField(validators=[validators.UUID()])
    submit = SubmitField(_("Remove"))


class AnnotateForm(FlaskForm):
    submission_id = HiddenField(validators=[validators.regexp(r"^\d+$")])
    ref_start = HiddenField(validators=[validators.regexp(r"^\d+$")])
    ref_end = HiddenField(validators=[validators.regexp(r"^\d+$")])
    ne_type = HiddenField()
    ctx_public = SubmitField()
    ctx_secret = SubmitField()
    lemma_public = SubmitField()
    lemma_secret = SubmitField()
    ne_type_public = SubmitField()
    ne_type_secret = SubmitField()
