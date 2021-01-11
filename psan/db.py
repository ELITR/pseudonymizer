import os

import psycopg2
import psycopg2.extras
from flask import Flask, g


def get_db():
    """Connect to the application's configured database. The connection
    is unique for each request and will be reused if this is called
    again.
    """
    if "db" not in g:
        g.db = psycopg2.connect(database=os.environ["DB_NAME"],
                                user=os.environ["DB_USER"],
                                password=os.environ["DB_PASSWORD"],
                                host=os.environ["DB_HOST"],
                                port="5432")
    return g.db


def get_cursor():
    return get_db().cursor(cursor_factory=psycopg2.extras.DictCursor)


def commit():
    get_db().commit()


def close_db(e=None):
    """If this request connected to the database, close the
    connection.
    """
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_app(app: Flask) -> None:
    """Register database functions with the Flask app. This is called by
    the application factory.
    """
    app.teardown_appcontext(close_db)
