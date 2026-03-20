-- V1__init.sql — Oracle
-- Replace with your actual schema. This file is executed once at startup by Flyway.
-- Note: configure your datasource URL in application.yml / environment variables.

CREATE TABLE example (
    id         NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR2(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL
);
