-- Runs once, when the db volume is first created.
-- Enables PostGIS in the main database and creates a separate database for the test suite.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE DATABASE crvr_test;

\connect crvr_test
CREATE EXTENSION IF NOT EXISTS postgis;
