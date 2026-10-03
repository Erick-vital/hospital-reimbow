#!/bin/sh
# Sólo lo ejecuta el entrypoint de PostgreSQL sobre un volumen vacío.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  --set=dev_password="$PG_DEV_PASSWORD" --set=test_password="$PG_TEST_PASSWORD" <<'SQL'
CREATE ROLE hospital_dev LOGIN PASSWORD :'dev_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE hospital_test LOGIN PASSWORD :'test_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE hospital_dev OWNER hospital_dev;
CREATE DATABASE hospital_test OWNER hospital_test;
REVOKE ALL ON DATABASE hospital_dev FROM PUBLIC;
REVOKE ALL ON DATABASE hospital_test FROM PUBLIC;
SQL
