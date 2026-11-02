-- Run only with the migration-owner connection. Password values are read from
-- the process environment and SQL-quoted by format(%L); they are never printed.
\getenv runtime_role ZINA_RUNTIME_DB_ROLE
\getenv runtime_password ZINA_RUNTIME_DB_PASSWORD

SELECT (rolsuper OR rolcreaterole) AS migration_owner_can_manage_roles
FROM pg_roles
WHERE rolname = current_user
\gset
\if :migration_owner_can_manage_roles
\else
\echo Migration owner must be superuser or have CREATEROLE privilege.
\quit 3
\endif

SELECT format(
    'CREATE ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'runtime_role',
    :'runtime_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_role')
\gexec

SELECT format(
    'ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'runtime_role',
    :'runtime_password'
)
\gexec

-- Remove memberships in both directions. NOINHERIT prevents automatic
-- privilege inheritance, but a member can still explicitly SET ROLE.
-- First remove parent roles granted to the runtime login.
SELECT format('REVOKE %I FROM %I', granted.rolname, :'runtime_role')
FROM pg_auth_members membership
JOIN pg_roles granted ON granted.oid = membership.roleid
JOIN pg_roles member ON member.oid = membership.member
WHERE member.rolname = :'runtime_role'
\gexec

-- Then remove the runtime login from every role that could SET ROLE into it.
SELECT format('REVOKE %I FROM %I', :'runtime_role', member.rolname)
FROM pg_auth_members membership
JOIN pg_roles member ON member.oid = membership.member
WHERE membership.roleid = (SELECT oid FROM pg_roles WHERE rolname = :'runtime_role')
\gexec

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'runtime_role')
\gexec
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SELECT format('REVOKE CREATE ON SCHEMA public FROM %I', :'runtime_role')
\gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'runtime_role')
\gexec
SELECT format(
    'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %I',
    :'runtime_role'
)
\gexec
SELECT format(
    'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO %I',
    :'runtime_role'
)
\gexec

-- Future migration-owned tables/sequences receive the same application DML
-- baseline. The consent audit table is narrowed again below after every run.
SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
    current_user,
    :'runtime_role'
)
\gexec
SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO %I',
    current_user,
    :'runtime_role'
)
\gexec

SELECT to_regclass('public.schema_migrations') IS NOT NULL AS has_schema_migrations \gset
\if :has_schema_migrations
SELECT format('REVOKE ALL ON TABLE public.schema_migrations FROM %I', :'runtime_role')
\gexec
\endif

SELECT to_regclass('public.contact_messaging_consent_events') IS NOT NULL AS has_consent_events \gset
\if :has_consent_events
REVOKE ALL ON TABLE public.contact_messaging_consent_events FROM PUBLIC;
SELECT format('REVOKE ALL ON TABLE public.contact_messaging_consent_events FROM %I', :'runtime_role')
\gexec
SELECT format('GRANT SELECT, INSERT ON TABLE public.contact_messaging_consent_events TO %I', :'runtime_role')
\gexec

-- The runtime API needs nextval/currval for ordinary inserts, not setval().
-- Narrow this immutable audit table's BIGSERIAL sequence even after earlier
-- provisioning runs may have granted UPDATE through the broad application ACL.
SELECT format(
    'REVOKE UPDATE ON SEQUENCE %s FROM %I',
    pg_get_serial_sequence('public.contact_messaging_consent_events', 'id'),
    :'runtime_role'
)
WHERE pg_get_serial_sequence('public.contact_messaging_consent_events', 'id') IS NOT NULL
\gexec

SELECT (
    pg_get_serial_sequence('public.contact_messaging_consent_events', 'id') IS NOT NULL
    AND has_sequence_privilege(
        :'runtime_role',
        pg_get_serial_sequence('public.contact_messaging_consent_events', 'id'),
        'USAGE'
    )
    AND has_sequence_privilege(
        :'runtime_role',
        pg_get_serial_sequence('public.contact_messaging_consent_events', 'id'),
        'SELECT'
    )
    AND NOT has_sequence_privilege(
        :'runtime_role',
        pg_get_serial_sequence('public.contact_messaging_consent_events', 'id'),
        'UPDATE'
    )
) AS consent_sequence_privileges_ok \gset
\if :consent_sequence_privileges_ok
\else
\echo Runtime role consent-event sequence must allow USAGE/SELECT but deny UPDATE.
\quit 3
\endif

SELECT (
    has_table_privilege(:'runtime_role', 'public.contact_messaging_consent_events', 'SELECT')
    AND has_table_privilege(:'runtime_role', 'public.contact_messaging_consent_events', 'INSERT')
    AND NOT has_table_privilege(:'runtime_role', 'public.contact_messaging_consent_events', 'UPDATE')
    AND NOT has_table_privilege(:'runtime_role', 'public.contact_messaging_consent_events', 'DELETE')
    AND NOT has_table_privilege(:'runtime_role', 'public.contact_messaging_consent_events', 'TRUNCATE')
    AND NOT has_table_privilege(:'runtime_role', 'public.contact_messaging_consent_events', 'REFERENCES')
    AND NOT has_table_privilege(:'runtime_role', 'public.contact_messaging_consent_events', 'TRIGGER')
) AS consent_privileges_ok \gset
\if :consent_privileges_ok
\else
\echo Runtime role consent-history privileges are not restricted as required.
\quit 3
\endif
\endif

SELECT NOT EXISTS (
    SELECT 1 FROM pg_class
    WHERE relowner = (SELECT oid FROM pg_roles WHERE rolname = :'runtime_role')
) AS no_owned_relations \gset
\if :no_owned_relations
\else
\echo Runtime role must not own database relations.
\quit 3
\endif

SELECT NOT EXISTS (
    SELECT 1 FROM pg_database
    WHERE datname = current_database()
      AND datdba = (SELECT oid FROM pg_roles WHERE rolname = :'runtime_role')
) AS no_owned_database \gset
\if :no_owned_database
\else
\echo Runtime role must not own the application database.
\quit 3
\endif

SELECT NOT has_database_privilege(:'runtime_role', current_database(), 'CREATE') AS no_database_create \gset
\if :no_database_create
\else
\echo Runtime role must not have CREATE privilege on the application database.
\quit 3
\endif

SELECT NOT has_schema_privilege(:'runtime_role', 'public', 'CREATE') AS no_public_schema_create \gset
\if :no_public_schema_create
\else
\echo Runtime role must not have CREATE privilege on the public schema.
\quit 3
\endif

SELECT NOT EXISTS (
    SELECT 1 FROM pg_namespace
    WHERE nspowner = (SELECT oid FROM pg_roles WHERE rolname = :'runtime_role')
) AS no_owned_schemas \gset
\if :no_owned_schemas
\else
\echo Runtime role must not own database schemas.
\quit 3
\endif

SELECT NOT EXISTS (
    SELECT 1 FROM pg_auth_members
    WHERE member = (SELECT oid FROM pg_roles WHERE rolname = :'runtime_role')
       OR roleid = (SELECT oid FROM pg_roles WHERE rolname = :'runtime_role')
) AS no_role_memberships \gset
\if :no_role_memberships
\else
\echo Runtime role must not inherit or assume another role.
\quit 3
\endif

SELECT (
    rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
    AND NOT rolinherit AND NOT rolreplication AND NOT rolbypassrls
) AS role_attributes_ok
FROM pg_roles
WHERE rolname = :'runtime_role'
\gset
\if :role_attributes_ok
\else
\echo Runtime role attributes are not restricted as required.
\quit 3
\endif
