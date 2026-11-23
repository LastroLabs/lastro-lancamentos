-- Plan NUC-01, D5: the two database roles. Run as a superuser; idempotent; no password here.
--   lastro_owner: owns the database and the tables; only the migrations connect as it.
--   lastro_app:   the API; reads and writes rows, cannot change the schema.
-- Neither role is superuser, creates databases or roles, or bypasses row level security.
-- Passwords are set by whoever runs this file (create_roles.sh or the test fixture).

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lastro_owner') THEN
        CREATE ROLE lastro_owner;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lastro_app') THEN
        CREATE ROLE lastro_app;
    END IF;
END
$$;

-- Also applied when the roles already exist, so a re-run fixes any drifted attribute.
ALTER ROLE lastro_owner WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION;
ALTER ROLE lastro_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION;
