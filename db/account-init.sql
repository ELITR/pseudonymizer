-- Initialize the PostgreSQL database.

-- Table
CREATE TYPE account_type AS ENUM ('USER', 'ADMIN');

CREATE TYPE submission_status AS ENUM ('NEW', 'RECOGNIZED', 'PRE_ANNOTATED', 'DONE'); 

CREATE TYPE annotation_decision AS ENUM ('PUBLIC', 'SECRET', 'NESTED');

CREATE TYPE annotation_source AS ENUM ('RULE', 'USER');

CREATE TYPE rule_type AS ENUM ('WORD_TYPE', 'LEMMA', 'NE_TYPE');

CREATE TABLE account (
    id                  INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    full_name           TEXT                        NOT NULL,
    type                account_type                NOT NULL,
    window_size         INT                         NOT NULL,
    email               TEXT                UNIQUE  NOT NULL,
    password            TEXT                        NOT NULL,
    created             TIMESTAMP                   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (email LIKE '%@%'),
    CHECK (window_size > 0)
);

CREATE TABLE submission (
    id          INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name        TEXT                        NOT NULL,
    uid         UUID                UNIQUE  NOT NULL,
    status      submission_status           NOT NULL DEFAULT 'NEW',
    num_tokens  INT,
    created     TIMESTAMP                   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (0 <= num_tokens)
);

CREATE TABLE annotation (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    submission      INT REFERENCES submission(id) ON DELETE CASCADE    NOT NULL,
    token_level     annotation_decision,
    rule_level      INT,
    label           INT REFERENCES label(id) ON DELETE SET NULL,
    source          annotation_source                                  NOT NULL DEFAULT 'RULE',
    ref_start       INT                                                NOT NULL,
    ref_end         INT                                                NOT NULL,    
    author          INT REFERENCES account(id) ON DELETE SET NULL,
    UNIQUE (submission, ref_start, ref_end),
    CHECK (ref_start <= ref_end)
);

CREATE TABLE label (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name            TEXT UNIQUE NOT NULL,
    replacement     TEXT NOT NULL
);

CREATE TABLE rule (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    type            rule_type                   NOT NULL,
    condition       TEXT[]                      NOT NULL,
    confidence      INT                         NOT NULL,
    author          INT REFERENCES account(id)  ON DELETE SET NULL,
    label           INT REFERENCES label(id)    ON DELETE SET NULL,
    source          INT REFERENCES annotation(id) ON DELETE CASCADE, -- cleanup from auto rules
    UNIQUE (type, condition)
);

CREATE TABLE annotation_rule (
    annotation      INT REFERENCES annotation(id) ON DELETE CASCADE    NOT NULL,
    rule            INT REFERENCES rule(id) ON DELETE CASCADE          NOT NULL,
    UNIQUE (annotation, rule)
);

CREATE PROCEDURE update_rule(rule_id integer, ammount integer)
LANGUAGE SQL
AS $$
UPDATE 
    annotation 
SET 
    rule_level = rule_level + ammount 
FROM 
    annotation_rule 
WHERE 
    annotation.id = annotation_rule.annotation 
    and annotation_rule.rule = rule_id;
$$;

CREATE OR REPLACE PROCEDURE annotatation_cleanup()
LANGUAGE SQL
AS $$
DELETE FROM annotation AS a WHERE a.token_level IS NULL AND a.rule_level = 0 AND NOT EXISTS (SELECT 1 FROM annotation_rule AS ar WHERE a.id = ar.annotation);
$$;

CREATE OR REPLACE FUNCTION before_rule_deletion_fnc() RETURNS trigger AS $emp_stamp$
    BEGIN
        CALL update_rule(OLD.id, -OLD.confidence);
        RETURN OLD;
    END;
$emp_stamp$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION after_rule_deletion_fnc() RETURNS trigger AS $emp_stamp$
    BEGIN
        CALL annotatation_cleanup();
        RETURN NULL;
    END;
$emp_stamp$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION rule_update_fn() RETURNS trigger AS $emp_stamp$
    BEGIN
        CALL update_rule(NEW.id, -OLD.confidence + NEW.confidence);
        RETURN NULL;
    END;
$emp_stamp$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION annotation_rule_insert_fn() RETURNS trigger AS $emp_stamp$
    BEGIN
        UPDATE 
            annotation 
        SET 
            rule_level = rule_level + rule.confidence
        FROM 
            rule 
        WHERE 
            annotation.id = NEW.annotation
            and rule.id = NEW.rule; 
        RETURN NULL;
   END;
$emp_stamp$ LANGUAGE plpgsql;

CREATE TRIGGER before_rule_deletion_trigger BEFORE DELETE 
    ON rule
    FOR EACH ROW
    EXECUTE PROCEDURE before_rule_deletion_fnc();

CREATE TRIGGER after_rule_deletion_trigger AFTER DELETE 
    ON rule
    FOR EACH ROW
    EXECUTE PROCEDURE after_rule_deletion_fnc();

CREATE TRIGGER rule_update_trigger AFTER UPDATE 
    OF confidence ON rule
    FOR EACH ROW
    EXECUTE PROCEDURE rule_update_fn();

CREATE TRIGGER annotation_rule_insert_trigger AFTER INSERT 
    ON annotation_rule
    FOR EACH ROW
    EXECUTE PROCEDURE annotation_rule_insert_fn(); 
