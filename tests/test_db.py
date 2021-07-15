import random

import pytest
from psan.tool.model import RuleType
from psan.db import commit, get_cursor
from flask.testing import FlaskClient
from psan import app


@pytest.fixture
def client():
    with app.test_client() as client:
        app.config["SERVER_NAME"] = "example.com"
        yield client


def test_rule_db(client: FlaskClient) -> None:
    """
    Test that 'rule' database exist and has access from Flask
    """
    with app.app_context():
        condition = ["test_word"]
        confidence = random.randint(10, 10000)
        # Test insert
        with get_cursor() as cursor:
            cursor.execute("DELETE FROM rule WHERE type = %s and condition = %s",
                           (RuleType.WORD_TYPE.value, condition))
            cursor.execute("INSERT INTO rule (type, condition, confidence) VALUES (%s, %s, %s)",
                           (RuleType.WORD_TYPE.value, condition, confidence))
            commit()
        # Test select
        with get_cursor() as cursor:
            cursor.execute("SELECT confidence FROM rule WHERE type = %s and condition = %s",
                           (RuleType.WORD_TYPE.value, condition))
            data = cursor.fetchone()
            assert data is not None
            assert data["confidence"] == confidence
            cursor.execute("DELETE FROM rule WHERE type = %s and condition = %s",
                           (RuleType.WORD_TYPE.value, condition))
            commit()
