---
name: postgres-query
description: Run read-only SQL queries against PostgreSQL databases. Connect via libpq environment variables and ~/.pgpass — no connection details exposed to the agent.
---

# PostgreSQL Query Skill

Run read-only queries against a PostgreSQL database. The bundled script uses [psycopg](https://www.psycopg.org/psycopg3/) (v3) with READ ONLY transactions — writes are rejected at the database level.

**Connection details are never known to the agent.** The user configures libpq environment variables (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`) and `~/.pgpass` before starting the agent session. The agent references `$PGHOST` etc. in commands — bash expands them at runtime, the literal values never enter the agent's context.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager) — installs dependencies automatically
- Python 3.10+
- Network access to the PostgreSQL target

## Setup — one-time by the user

Before using this skill, the user must configure three things **outside the agent session**:

### 1. Use a dedicated SELECT-only role (recommended)

Do **not** connect with a superuser or other admin role. The script rejects **every** query when the session role has any elevated privilege flag — a dedicated read-only role is mandatory, not optional. The `SELECT`-only role below is the only supported configuration.

Create a role with only the privileges it needs:

```sql
CREATE ROLE readonly_user LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE your_db TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;
```

Then set `PGUSER=readonly_user` in the environment.

### 2. libpq environment variables

Set these in `~/.bashrc`, `~/.zshrc`, or export before starting the agent:

```bash
export PGHOST=your-db-host.example.com
export PGPORT=5432
export PGDATABASE=your-db-name
export PGUSER=your-username
```

### 3. ~/.pgpass for password

```bash
echo "your-db-host.example.com:5432:your-db-name:your-username:your-password" >> ~/.pgpass
chmod 600 ~/.pgpass
```

PostgreSQL ignores `.pgpass` if permissions are not `600`.

## What the agent does

### 1. Verify the session is a plain read-only role

Run the privilege check **before any query** to confirm the environment is set up correctly:

```bash
uv run scripts/query.py \
  "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, rolreplication FROM pg_roles WHERE rolname = current_user" \
  --format table
```

This is a gate, not just reporting: the script rejects every query with exit code 3 when the session role has any elevated flag (`rolsuper`, `rolcreaterole`, `rolcreatedb`, `rolbypassrls`, `rolreplication`) or cannot be verified in `pg_roles`. No exceptions — a privileged session never executes a query, even a "harmless" read-only one.

Report the result to the user:

- All flags `false` → "Session is a plain read-only role. Proceeding."
- Any flag `true` or rejection with exit code 3 → "Session is not a read-only role — queries are rejected. Configure `readonly_user` (see Setup) and restart the agent session." Do not attempt to work around the rejection.

### 2. Check if .pgpass exists

```bash
test -f ~/.pgpass && echo "found" || echo "missing"
```

If `.pgpass` is missing, tell the user:

> Please create `~/.pgpass` with one line per database:
>
> ```
> hostname:port:databasename:username:password
> ```
>
> Then run `chmod 600 ~/.pgpass`.

Do not ask for or accept connection details. The user configures them outside the agent session.

### 3. Run the query

The script uses `$PGHOST`, `$PGPORT`, `$PGDATABASE`, `$PGUSER` from the environment and `~/.pgpass` for the password. Reference these variables in commands — bash expands them, the agent never sees the actual values. The script validates the SQL shape (single read-only `SELECT`, CTEs allowed) and the session role before anything reaches the database — if the query is rejected (shape or privileges), report the error verbatim and stop. Do not attempt to work around a rejection.

## Available script

| Script             | Description                                              |
| ------------------ | -------------------------------------------------------- |
| `scripts/query.py` | Execute a read-only PostgreSQL query (SELECT-only validation + role privilege gate), results as JSON/CSV/table |

Uses [PEP 723](https://peps.python.org/pep-0723/) inline metadata — `uv run` installs dependencies on demand. No manual install step needed.

## Usage

**No connection flags needed.** The script reads `$PGHOST`, `$PGPORT`, `$PGDATABASE`, `$PGUSER` from the environment and authenticates via `~/.pgpass`.

```bash
uv run scripts/query.py [OPTIONS] [QUERY]
```

### Query sources

```bash
# Inline query
uv run scripts/query.py "SELECT now()"

# Read from file
uv run scripts/query.py --file queries/latest-users.sql

# Pipe from stdin
echo "SELECT 1 AS test" | uv run scripts/query.py

# Stdin via --file -
uv run scripts/query.py --file - < queries/script.sql
```

### Output formats

```bash
# JSON (default) — pipe into jq or consume as structured data
uv run scripts/query.py "SELECT * FROM users" --format json

# CSV — spreadsheets or pandas
uv run scripts/query.py "SELECT * FROM users" --format csv

# Table — human-readable inspection
uv run scripts/query.py "SELECT * FROM users" --format table
```

### Other flags

| Flag            | Description                                   |
| --------------- | --------------------------------------------- |
| `--timeout SEC` | Query timeout in seconds (default: 30)        |
| `--verbose`     | Print connection info and row count to stderr |

**Advanced — explicit overrides** (only when the user explicitly asks):

- `--host`, `--port`, `--dbname`, `--user`, `--password` — override individual env vars
- `--conn-string` — full connection URI (overrides everything)
- `--sslmode` — SSL mode (default: libpq default)

These exist for one-off overrides. The standard workflow uses env vars + `.pgpass`.

## Examples

### Schema inspection

```bash
# List all tables
uv run scripts/query.py \
  "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema') ORDER BY table_schema, table_name"

# Describe a table
uv run scripts/query.py \
  "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'users' ORDER BY ordinal_position"
```

### Ad-hoc queries

```bash
# Count rows
uv run scripts/query.py "SELECT count(*) FROM orders"

# Recent records
uv run scripts/query.py \
  "SELECT id, created_at, status FROM orders ORDER BY created_at DESC LIMIT 10" \
  --format table --verbose
```

### Debug a slow query

```bash
# Check what's running
uv run scripts/query.py \
  "SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC" \
  --format table

# EXPLAIN ANALYZE a slow query (executes it — the inner statement must be read-only)
uv run scripts/query.py \
  "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE status = 'pending'" \
  --format table
```

## Safety

- **Query-shape validation (static, before connecting):** the script parses the input with sqlglot (Postgres dialect) and accepts only a single read-only `SELECT` — CTEs and set operations (`UNION`/`INTERSECT`/`EXCEPT`) are allowed, and anything inside a CTE must also be read-only. `EXPLAIN` / `EXPLAIN ANALYZE` is allowed only when it wraps a read-only `SELECT` (it executes the query, so the inner statement must pass the same validation). DML/DDL (`INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, …), transaction control, `COPY`, `LISTEN`/`NOTIFY`, locking reads (`SELECT ... FOR UPDATE`), multi-statement input, and unparseable SQL are rejected with exit code 3 before a connection is ever made. Note: this is statement-level validation — it does not inspect function bodies (e.g. `SELECT nextval(...)` still parses as a `SELECT`); read-only side effects are limited by the READ ONLY transaction and the privilege gate below.
- **Privilege gate (deterministic, no exceptions):** before every query the script checks the session role's flags (`rolsuper`, `rolcreaterole`, `rolcreatedb`, `rolbypassrls`, `rolreplication`) and exits with code 3 — rejecting the query — if any flag is set or the role cannot be verified in `pg_roles`. A privileged session never executes a query, even a read-only one.
- The script sets `SET TRANSACTION READ ONLY` before every query and uses PostgreSQL's single-statement extended protocol. Persistent `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, transaction-control escapes, and other database writes are rejected.
- Connection errors, query errors, and timeouts print descriptive messages to stderr and exit with code 1; validation rejections (query shape or privileges) exit with code 3.
- Structured output goes to stdout only — diagnostics are always on stderr, so JSON/CSV output remains parseable.
