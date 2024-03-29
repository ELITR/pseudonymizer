import os

from flask import (Flask, after_this_request, g, redirect, render_template,
                   request, send_from_directory, url_for)
from flask_babel import Babel
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect

from psan import celery, db
from psan.auth import REGISTER_TOKEN_NAME, generate_auth_token


def build_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # Configs
    # Load the default configuration
    app.config.from_object("config.default")
    # Load the configuration from the instance folder
    app.config.from_pyfile('config.py', silent=True)
    # Load config according to run environment
    # Variables defined here will override those in the default configuration
    if app.debug:
        app.config.from_object("config.debug")
    else:
        app.config.from_object("config.production")
    # Save whitespace in templates
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.trim_blocks = True

    celery.init_celery(app)
    db.init_app(app)

    # Bootstrap
    Bootstrap(app)
    init_translations(app)

    # CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico', mimetype='image/vnd.microsoft.icon')

    # Redirection
    app.add_url_rule("/", endpoint="index")

    # apply the blueprints to the app
    from psan import auth
    app.register_blueprint(auth.bp)
    from psan import account
    app.register_blueprint(account.bp)
    from psan import submission
    app.register_blueprint(submission.bp)
    from psan import annotate
    app.register_blueprint(annotate.bp)
    from psan import rule
    app.register_blueprint(rule.bp)
    from psan import label
    app.register_blueprint(label.bp)
    from psan import generate
    app.register_blueprint(generate.bp)

    # Create register token
    if os.environ.get("ALLOW_TOKEN_REGISTRATION", default="0") == "1":
        if app.config.get("SERVER_NAME"):
            with app.app_context():
                path = url_for('auth.register', token=generate_auth_token(REGISTER_TOKEN_NAME), _external=True)
        else:
            with app.test_request_context("localhost"):  # workaround for missing SERVER_NAME
                path = "http://localhost:5000" + \
                    url_for('auth.register', token=generate_auth_token(REGISTER_TOKEN_NAME))
            app.logger.info(
                f"You can register new user at {path}")

    return app


def init_translations(app: Flask) -> None:
    """
    Enable babel for `_(str)` method, language detection and sets "page" for lang switching
    """
    babel = Babel(app)

    @app.before_request
    def detect_user_language():
        # Check user language preference form cookie
        language = request.cookies.get('lang')

        if language is None:
            # Try autodetect language
            g.lang = request.accept_languages.best_match(["en"], default="en")

            # Save detected value as a cookie
            @after_this_request
            def remember_language(response):
                response.set_cookie('lang', g.lang)
                return response
        else:
            if language in ["cs", "en"]:
                g.lang = language
            else:
                raise NotImplementedError()

    @app.route("/translate")
    def switch_lang():
        """
        Switch lang from `en` to `cs` and vice versa
        """
        if g.lang == "cs":
            g.lang = "en"
        else:
            g.lang = "cs"

        # Save updated value to cookie
        response = redirect(request.referrer)
        response.set_cookie('lang', g.lang)
        return response

    @babel.localeselector
    def get_locale():
        return g.lang


app = build_app()
