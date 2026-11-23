#!/bin/sh
# Plan NUC-01, D5. Runs once, from /docker-entrypoint-initdb.d of the `db` service, on an
# empty data directory: creates the roles (create_roles.sql), sets their passwords from the
# environment (.env) and hands the database over to lastro_owner.
set -e

: "${OWNER_DB_PASSWORD:?defina OWNER_DB_PASSWORD no .env (veja o .env.example)}"
: "${APP_DB_PASSWORD:?defina APP_DB_PASSWORD no .env (veja o .env.example)}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --file /lastro-bootstrap/create_roles.sql

# psql variables (:'name' and :"name") quote the values; the heredoc is not expanded by sh.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v owner_pw="$OWNER_DB_PASSWORD" \
    -v app_pw="$APP_DB_PASSWORD" \
    -v database_name="$POSTGRES_DB" <<'SQL'
ALTER ROLE lastro_owner WITH PASSWORD :'owner_pw';
ALTER ROLE lastro_app WITH PASSWORD :'app_pw';
ALTER DATABASE :"database_name" OWNER TO lastro_owner;
SQL
