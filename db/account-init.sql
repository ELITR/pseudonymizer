-- Initialize the PostgreSQL database.

-- Database
CREATE DATABASE psan_db;
\c psan_db;

-- Table
CREATE TYPE account_type AS ENUM ('USER', 'ADMIN');

CREATE TABLE account (
    id                  SERIAL PRIMARY KEY,
    full_name           TEXT                        NOT NULL,
    type                account_type                NOT NULL,
    login               TEXT                UNIQUE  NOT NULL,
    password            TEXT                        NOT NULL,
    created             TIMESTAMP                   NOT NULL DEFAULT CURRENT_TIMESTAMP
);