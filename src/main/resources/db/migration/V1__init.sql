-- Initial schema: users (JWT auth) and employees.

CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP NOT NULL
);

CREATE TABLE employees (
    id            BIGSERIAL PRIMARY KEY,
    first_name    VARCHAR(100) NOT NULL,
    last_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE,
    phone         VARCHAR(50),
    department    VARCHAR(100) NOT NULL,
    designation   VARCHAR(100) NOT NULL,
    salary        NUMERIC(14, 2) NOT NULL,
    joining_date  DATE NOT NULL,
    status        VARCHAR(30) NOT NULL,
    created_at    TIMESTAMP NOT NULL,
    updated_at    TIMESTAMP NOT NULL
);

CREATE INDEX idx_employees_department ON employees (department);
CREATE INDEX idx_employees_email ON employees (email);
CREATE INDEX idx_employees_last_first_name ON employees (last_name, first_name);
