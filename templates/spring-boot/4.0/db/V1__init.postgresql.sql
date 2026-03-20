-- V1__init.sql — PostgreSQL
-- Replace with your actual schema. This file is executed once at startup by Flyway.

CREATE TABLE IF NOT EXISTS example (
    id         BIGSERIAL     PRIMARY KEY,
    name       VARCHAR(255)  NOT NULL,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
