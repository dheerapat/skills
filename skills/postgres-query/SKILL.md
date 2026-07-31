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

Before using this skill, the user must configure two things **outside the agent session**:

### 1. libpq environment variables

Set these in `~/.bashrc`, `~/.zshrc`, or export before starting the agent:

```bash
export PGHOST=your-db-host.example.com
export PGPORT=5432
export PGDATABASE=your-db-name
export PGUSER=your-username
```

### 2. ~/.pgpass for password

```bash
echo "your-db-host.example.com:5432:your-db-name:your-username:your-password" >> ~/.pgpass
chmod 600 ~/.pgpass
```

PostgreSQL ignores `.pgpass` if permissions are not `600`.

## What the agent does

### Check if .pgpass exists

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

The script uses `$PGHOST`, `$PGPORT`, `$PGDATABASE`, `$PGUSER` from the environment and `~/.pgpass` for the password. Reference these variables in commands — bash expands them, the agent never sees the actual values.

## Available script

| Script             | Description                                              |
| ------------------ | -------------------------------------------------------- |
| `scripts/query.py` | Execute a read-only SQL query, results as JSON/CSV/table |

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
```

## Safety

- The script sets `SET TRANSACTION READ ONLY` before every query and uses PostgreSQL's single-statement extended protocol. Persistent `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, transaction-control escapes, and other database writes are rejected even when the connection user is a superuser.
- This is a database-state guard, not a security boundary for admin credentials. A superuser can invoke read-only-transaction-compatible operations with external or operational side effects, such as `COPY ... TO PROGRAM` or privileged functions. Use a dedicated `SELECT`-only role when untrusted queries or a strong read-only guarantee are involved.
- Connection errors, query errors, and timeouts print descriptive messages to stderr and exit with code 1.
- Structured output goes to stdout only — diagnostics are always on stderr, so JSON/CSV output remains parseable.
