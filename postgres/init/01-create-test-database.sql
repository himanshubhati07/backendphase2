-- This runs once on first initialization of the PostgreSQL data volume.
-- The primary database is created by POSTGRES_DB; tests use this separate DB.
CREATE DATABASE task_manager_test;
