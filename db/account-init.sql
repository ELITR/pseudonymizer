-- Initialize the PostgreSQL database.

-- Table
CREATE TYPE account_type AS ENUM ('USER', 'ADMIN');

CREATE TYPE submission_status AS ENUM ('NEW', 'RECOGNIZED', 'ANNOTATED', 'DONE');

CREATE TYPE annotation_decision AS ENUM ('CTX_SECRET', 'CTX_PUBLIC', 'RULE_SECRET', 'RULE_PUBLIC', 'UNDECIDED');

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
    status      submission_status           NOT NULL
);

CREATE TABLE annotation (
    id           SERIAL PRIMARY KEY,
    submission   INT REFERENCES submission(id) ON DELETE CASCADE    NOT NULL,
    ne_id        INT                                                NOT NULL,
    decision     annotation_decision                                NOT NULL DEFAULT 'UNDECIDED',
    UNIQUE (submission, candidate_id)
);