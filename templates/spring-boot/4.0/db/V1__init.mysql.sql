-- V1__init.sql — MySQL
-- Replace with your actual schema. This file is executed once at startup by Flyway.

CREATE TABLE IF NOT EXISTS example (
    id         BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(255)  NOT NULL,
    created_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
