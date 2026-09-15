# Sources

Official documentation for all three skills (sql-king, sql-security, rls-security).
Current as of September 2026. Where this skill and the official documentation disagree, the
documentation wins — especially for Supabase, where defaults and key formats are actively
changing.

---

## Start here (read in this order if the topic is new)

1. Supabase — Understanding Row Level Security:
   https://supabase.com/docs/guides/database/postgres/row-level-security
2. Supabase — API keys explained:
   https://supabase.com/docs/guides/getting-started/api-keys
3. Supabase — Securing your Data API (grants and RLS together):
   https://supabase.com/docs/guides/api/securing-your-api
4. Postgres — Privileges (the underlying model):
   https://www.postgresql.org/docs/current/ddl-priv.html

---

## Queries and schema

- Postgres — Data types: https://www.postgresql.org/docs/current/datatype.html
- Postgres — Constraints: https://www.postgresql.org/docs/current/ddl-constraints.html
- Postgres — Indexes: https://www.postgresql.org/docs/current/indexes.html
- Postgres — CREATE INDEX: https://www.postgresql.org/docs/current/sql-createindex.html
- Postgres — Using EXPLAIN: https://www.postgresql.org/docs/current/using-explain.html
- Postgres — pg_stat_statements: https://www.postgresql.org/docs/current/pgstatstatements.html
- Postgres — ALTER TABLE (locking): https://www.postgresql.org/docs/current/sql-altertable.html
- Supabase — Tables and data types: https://supabase.com/docs/guides/database/tables
- Supabase — Joins and nested selects: https://supabase.com/docs/guides/database/joins-and-nesting
- Supabase — Database functions: https://supabase.com/docs/guides/database/functions
- Supabase — Generating TypeScript types: https://supabase.com/docs/guides/api/rest/generating-types

## Migrations and operations

- Supabase — Local development / CLI: https://supabase.com/docs/guides/local-development/overview
- Supabase — Database migrations: https://supabase.com/docs/guides/deployment/database-migrations
- Supabase — Backups: https://supabase.com/docs/guides/platform/backups
- Supabase — Connection management: https://supabase.com/docs/guides/database/connection-management
- Supabase — Pooling and limits:
  https://supabase.com/docs/guides/database/connecting-to-postgres/pooling-and-limits

## Keys and secrets

- Supabase — API keys: https://supabase.com/docs/guides/getting-started/api-keys
- Supabase — Migrating to publishable and secret keys:
  https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys
- Supabase — Key change announcement and timetable:
  https://github.com/orgs/supabase/discussions/29260
- Supabase — Rotating legacy keys:
  https://supabase.com/docs/guides/troubleshooting/rotating-anon-service-and-jwt-secrets-1Jq6yd

## Roles and privileges

- Postgres — Database roles: https://www.postgresql.org/docs/current/database-roles.html
- Postgres — Role attributes: https://www.postgresql.org/docs/current/role-attributes.html
- Postgres — Role membership: https://www.postgresql.org/docs/current/role-membership.html
- Postgres — GRANT: https://www.postgresql.org/docs/current/sql-grant.html
- Postgres — REVOKE: https://www.postgresql.org/docs/current/sql-revoke.html
- Postgres — ALTER DEFAULT PRIVILEGES:
  https://www.postgresql.org/docs/current/sql-alterdefaultprivileges.html
- Postgres — DROP DATABASE: https://www.postgresql.org/docs/current/sql-dropdatabase.html
- Postgres — DROP ROLE: https://www.postgresql.org/docs/current/sql-droprole.html
- Supabase — Using custom schemas: https://supabase.com/docs/guides/api/using-custom-schemas

## Row level security

- Postgres — Row security policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Postgres — CREATE POLICY: https://www.postgresql.org/docs/current/sql-createpolicy.html
- Postgres — CREATE FUNCTION (SECURITY DEFINER):
  https://www.postgresql.org/docs/current/sql-createfunction.html
- Postgres — Function volatility: https://www.postgresql.org/docs/current/xfunc-volatility.html
- Supabase — Row Level Security: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase — Storage access control: https://supabase.com/docs/guides/storage/security/access-control

## Rate limiting and abuse

- Supabase — Auth rate limits: https://supabase.com/docs/guides/auth/rate-limits
- Supabase — Rate limiting edge functions:
  https://supabase.com/docs/guides/functions/examples/rate-limiting
- Supabase — Securing your API (pre-request function):
  https://supabase.com/docs/guides/api/securing-your-api

## Injection and validation

- OWASP — SQL Injection Prevention Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- OWASP — Top 10: https://owasp.org/www-project-top-ten/
- Postgres — Dynamic SQL in PL/pgSQL:
  https://www.postgresql.org/docs/current/plpgsql-statements.html#PLPGSQL-STATEMENTS-EXECUTING-DYN
- Zod: https://zod.dev

## Testing

- Supabase — pgTAP testing: https://supabase.com/docs/guides/local-development/testing/pgtap-extended
- pgTAP reference: https://pgtap.org/documentation.html

---

## Verified 2026-09-15

Re-checked against the pages above on 2026-09-15: legacy `anon`/`service_role` deprecated by end of
2026; projects restored or created from 2025-11-01 have no legacy keys; several secret keys per
project; Auth token bucket per IP with capacity 30, `Sb-Forwarded-For` needs an `sb_secret_` key and
explicit enablement; existing projects still auto-grant `anon`/`authenticated`/`service_role` on new
`public` tables (revoke via `alter default privileges for role postgres`); `pgrst.db_pre_request` is
Data-API-only.

## A note on freshness

Two things are changing right now and should be checked before any larger decision:

1. **Key migration**: `anon` and `service_role` are being retired by the end of 2026, and
   projects created from November 2025 onward no longer have them.
2. **Default privileges**: Supabase is moving to a default where new tables in `public` no
   longer receive automatic grants for `anon` and `authenticated`. Until then, revoke manually.
