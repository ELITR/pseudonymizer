import pytest
from flask import url_for
from flask.testing import FlaskClient
from psan import app

DEFAULT_HEADERS = [("Accept-Language", "en_US")]


@pytest.fixture
def client():
    with app.test_client() as client:
        app.config["SERVER_NAME"] = "example.com"
        yield client


def test_index(client: FlaskClient) -> None:
    """
    Test that index is accessible without login
    """
    with app.app_context():
        response = client.get(url_for("index"), headers=DEFAULT_HEADERS)
    assert response.status_code == 200
    assert b"Revision:" in response.data


def test_login(client: FlaskClient) -> None:
    with app.app_context():
        response = client.get(url_for("auth.login"), headers=DEFAULT_HEADERS)
    assert response.status_code == 200
    assert b"Log in" in response.data


def test_register(client: FlaskClient) -> None:
    with app.app_context():
        response = client.get(url_for("auth.register"), headers=DEFAULT_HEADERS)
    assert response.status_code == 200
    assert b"Create a new account" in response.data


def test_reset(client: FlaskClient) -> None:
    with app.app_context():
        response = client.get(url_for("auth.reset"), headers=DEFAULT_HEADERS)
    assert response.status_code == 200
    assert b"Having trouble logging in?" in response.data


def test_restricted(client: FlaskClient) -> None:
    for page in ["account.index", "account.delete_account", "account.change_password",
                 "annotate.index", "annotate.show", "submission.index"]:
        with app.app_context():
            login_redirect(url_for(page), client)


def login_redirect(page: str, client: FlaskClient) -> None:
    response = client.get(page, headers=DEFAULT_HEADERS)
    assert response.status_code == 302
    assert response.location == url_for("auth.login", _external=True)
