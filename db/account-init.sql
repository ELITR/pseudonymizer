-- Initialize the PostgreSQL database.

-- Table
CREATE TYPE account_type AS ENUM ('USER', 'ADMIN');

CREATE TYPE submission_status AS ENUM ('NEW', 'RECOGNIZED', 'ANNOTATED', 'DONE');

CREATE TABLE account (
    id                  SERIAL PRIMARY KEY,
    full_name           TEXT                        NOT NULL,
    type                account_type                NOT NULL,
    email               TEXT                UNIQUE  NOT NULL,
    password            TEXT                        NOT NULL,
    created             TIMESTAMP                   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE submission (
    id          SERIAL PRIMARY KEY,
    name        TEXT                        NOT NULL,
    uid         UUID                UNIQUE  NOT NULL,
    status      submission_status           NOT NULL,
    candidates  integer
);
