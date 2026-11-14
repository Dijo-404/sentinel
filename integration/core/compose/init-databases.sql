-- V1 sandbox Postgres: one instance, separate databases per peer that needs SQL.
-- No production credentials. Passwords are local demo only.

CREATE USER api WITH PASSWORD 'api';
CREATE USER workflow WITH PASSWORD 'workflow';
CREATE USER ledger WITH PASSWORD 'ledger';
CREATE USER dispatcher WITH PASSWORD 'dispatcher';
CREATE USER verifier WITH PASSWORD 'verifier';
CREATE USER policy WITH PASSWORD 'policy';
CREATE USER evidence WITH PASSWORD 'evidence';

CREATE DATABASE sentinel_api OWNER api;
CREATE DATABASE workflow OWNER workflow;
CREATE DATABASE action_ledger OWNER ledger;
CREATE DATABASE sentinel_demo_dispatcher OWNER dispatcher;
CREATE DATABASE sentinel_demo_verifier OWNER verifier;
CREATE DATABASE policy OWNER policy;
CREATE DATABASE evidence OWNER evidence;

GRANT ALL PRIVILEGES ON DATABASE sentinel_api TO api;
GRANT ALL PRIVILEGES ON DATABASE workflow TO workflow;
GRANT ALL PRIVILEGES ON DATABASE action_ledger TO ledger;
GRANT ALL PRIVILEGES ON DATABASE sentinel_demo_dispatcher TO dispatcher;
GRANT ALL PRIVILEGES ON DATABASE sentinel_demo_verifier TO verifier;
GRANT ALL PRIVILEGES ON DATABASE policy TO policy;
GRANT ALL PRIVILEGES ON DATABASE evidence TO evidence;
