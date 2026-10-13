-- Runs once, on first start of the PostgreSQL container: a separate database for the automated tests.
CREATE DATABASE nimbus_test OWNER nimbus;
