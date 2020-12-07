from collections import Iterable
from typing import Dict, List, Optional
import os

import psycopg2
import psycopg2.extras
from flask import g
from flask import Flask


def get_db():
    """Connect to the application's configured database. The connection
    is unique for each request and will be reused if this is called
    again.
    """
    if "g.db_proxy" not in g:
        g.db_proxy = PostgresProxy()
    return g.db_proxy


def close_db(e=None):
    """If this request connected to the database, close the
    connection.
    """
    db_proxy = g.pop("db_proxy", None)

    if db_proxy is not None:
        db_proxy.close()


def init_app(app: Flask) -> None:
    """Register database functions with the Flask app. This is called by
    the application factory.
    """
    app.teardown_appcontext(close_db)


class PostgresProxy:
    def __init__(self):
        self.db = psycopg2.connect(database=os.environ["DB_NAME"],
                                   user=os.environ["DB_USER"],
                                   password=os.environ["DB_PASSWORD"],
                                   host=os.environ["DB_HOST"],
                                   port="5432")
        self.cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def execute(self, sql: str, parameters: Iterable) -> None:
        self.cursor.execute(sql, parameters)

    def fetchone(self, sql: str, parameters: Iterable) -> Optional[Dict]:
        self.cursor.execute(sql, parameters)
        return self.cursor.fetchone()

    def fetchall(self, sql: str, parameters: Iterable) -> Optional[List[Dict]]:
        self.cursor.execute(sql, parameters)
        return self.cursor.fetchall()

    def commit(self) -> None:
        self.db.commit()

    def close(self) -> None:
        self.cursor.close()
        self.db.close()
