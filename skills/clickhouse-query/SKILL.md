---
name: clickhouse-query
description: Run read-only SQL queries against ClickHouse databases. Connect via CLICKHOUSE_* environment variables — no connection details exposed to the agent. Queries are statically validated (single SELECT only) and the session user must hold only direct SELECT grants.
---

# ClickHouse Query Skill

Run read-only queries against a ClickHouse database. The bundled script enforces read-only at three layers before anything meaningful reaches the database:

1. **Static shape validation** — sqlglot (ClickHouse dialect) accepts only a single read-only `SELECT` (CTEs and set operations allowed). DML/DDL, `SHOW`/`GRANT`/`REVOKE`/`OPTIMIZE`, `DESCRIBE`, `EXPLAIN`, multi-statement input, and unparseable SQL are rejected with exit code 3 **before a connection is made**.
1. **Side-effect denylist** — `INTO OUTFILE` (writes a file on the server), table functions with external I/O (`url()`, `s3()`, `file()`, `remote()`, …) and `sleep()`/`sleepEachRow()` are rejected.
1. **Privilege gate** — before every query the script runs `SHOW GRANTS`; the session user must hold only direct `SELECT` grants. Anything else (including `GRANT ALL` and role-based grants) is rejected with exit code 3. A dedicated SELECT-only user is **mandatory, not optional**.

Server-side `SET readonly = 2` remains as defense-in-depth — persistent `INSERT`/`ALTER`/`DROP`/mutations are rejected by the database with error 164 (`READONLY`).

**Connection details are never known to the agent.** The user configures `CLICKHOUSE_*` environment variables before starting the agent session. The agent references `$CLICKHOUSE_HOST` etc. in commands — bash expands them at runtime, the literal values never enter the agent's context.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager) — installs dependencies automatically
- Python 3.10+
- Network access to the ClickHouse HTTP port (8123 plain, 8443 TLS)

## Setup — one-time by the user

Before using this skill, the user must configure two things **outside the agent session**:

### 1. Use a dedicated SELECT-only user (mandatory — enforced)

Do **not** connect with an admin or `default` account that has broad privileges. The script rejects **every** query with exit code 3 when the session user holds any grant other than direct `SELECT` grants — a dedicated SELECT-only user is mandatory, not optional. The user below is the only supported configuration.

Create a user with only `SELECT` grants:

```sql
CREATE USER readonly_user IDENTIFIED WITH plaintext_password BY '...';
CREATE SETTINGS PROFILE readonly_profile SETTINGS readonly=2;
ALTER USER readonly_user SETTINGS PROFILE 'readonly_profile';
GRANT SELECT ON your_database.* TO readonly_user;
```

Grant `SELECT` **directly to the user** — role-based grants are also rejected by the gate. Then set `CLICKHOUSE_USER=readonly_user` in the environment.

### 2. Configure environment variables

```bash
export CLICKHOUSE_HOST=your-host.example.com    # ClickHouse Cloud: hostname from the console
export CLICKHOUSE_PORT=8123                     # 8123 plain HTTP, 8443 HTTPS
export CLICKHOUSE_DATABASE=default
export CLICKHOUSE_USER=default
export CLICKHOUSE_PASSWORD=your-password
export CLICKHOUSE_SECURE=false                  # true for HTTPS/TLS — required for ClickHouse Cloud
```

Set these in `~/.bashrc`, `~/.zshrc`, or export before starting the agent. For ClickHouse Cloud: open the service in the console → **Connect** → **HTTPS**, and use that hostname with `CLICKHOUSE_PORT=8443` and `CLICKHOUSE_SECURE=true`.

## What the agent does

### 1. Check that the connection is configured

```bash
test -n "$CLICKHOUSE_HOST" && test -n "$CLICKHOUSE_PASSWORD" && echo "configured" || echo "missing"
```

If missing, tell the user:

> Please configure the ClickHouse connection outside this session:
>
> ```bash
> export CLICKHOUSE_HOST=...
> export CLICKHOUSE_PORT=8123
> export CLICKHOUSE_DATABASE=default
> export CLICKHOUSE_USER=default
> export CLICKHOUSE_PASSWORD=...
> export CLICKHOUSE_SECURE=false
> ```
>
> Then restart the agent session.

Do not ask for or accept connection details. The user configures them outside the agent session. The script reads `$CLICKHOUSE_HOST`, `$CLICKHOUSE_PORT`, `$CLICKHOUSE_DATABASE`, `$CLICKHOUSE_USER`, `$CLICKHOUSE_PASSWORD`, `$CLICKHOUSE_SECURE` from the environment — reference these variables in commands, bash expands them, the agent never sees the actual values.

### 2. Verify the session is a SELECT-only user

Run the privilege check before any query to confirm the environment is set up correctly:

```bash
uv run scripts/query.py --check-privileges
```

This is a gate, not just reporting: the script rejects every query with exit code 3 when the session user holds any grant other than direct `SELECT` grants (see Safety). No exceptions — a privileged session never executes a query, even a "harmless" read-only one.

Report the result to the user:

- Every line is `GRANT SELECT ...` → "Session is SELECT-only. Proceeding."
- Any other line (e.g. `GRANT ALL ON *.* TO default WITH GRANT OPTION`) or rejection with exit code 3 → "Session is not a SELECT-only user — queries are rejected. Configure `readonly_user` (see Setup) and restart the agent session." Do not attempt to work around the rejection.

### 3. Run the query

The script reads `$CLICKHOUSE_HOST`, `$CLICKHOUSE_PORT`, `$CLICKHOUSE_DATABASE`, `$CLICKHOUSE_USER`, `$CLICKHOUSE_PASSWORD`, `$CLICKHOUSE_SECURE` from the environment. Reference these variables in commands — bash expands them, the agent never sees the actual values. The script validates the SQL shape (single read-only `SELECT`, CTEs allowed) and the session grants **before the query reaches the database** — if the query is rejected (shape or privileges), report the error verbatim and stop. Do not attempt to work around a rejection.

## Available script

| Script             | Description                                                                                                                      |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/query.py` | Execute a read-only ClickHouse query (SELECT-only validation + side-effect denylist + privilege gate), results as JSON/CSV/table |

Uses [PEP 723](https://peps.python.org/pep-0723/) inline metadata — `uv run` installs dependencies on demand. No manual install step needed.

## Usage

**No connection flags needed.** The script reads the `CLICKHOUSE_*` environment variables described above.

```bash
uv run scripts/query.py [OPTIONS] [QUERY]
```

### Query sources

```bash
# Inline query
uv run scripts/query.py "SELECT now()"

# Read from file
uv run scripts/query.py --file queries/latest-events.sql

# Pipe from stdin
echo "SELECT 1 AS test" | uv run scripts/query.py

# Stdin via --file -
uv run scripts/query.py --file - < queries/script.sql
```

### Output formats

```bash
# JSON (default) — pipe into jq or consume as structured data
uv run scripts/query.py "SELECT * FROM events" --format json

# CSV — spreadsheets or pandas
uv run scripts/query.py "SELECT * FROM events" --format csv

# Table — human-readable inspection
uv run scripts/query.py "SELECT * FROM events" --format table
```

### Other flags

| Flag                 | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--timeout SEC`      | Server-side `max_execution_time` in seconds (default: 30, `0` = unlimited). Sent only when the server permits it (the setting is not READONLY for the session); otherwise the client read timeout and the wall-clock deadline below still bound the run. A wall-clock deadline of `--timeout` + 70s also bounds the whole run (connect, gate, query, transfer) — a stuck run aborts instead of hanging. |
| `--check-privileges` | Print the session user's grants and verify they are SELECT-only, then exit (0 = ok, 3 = rejected)                                                                                                                                                                                                                                                                                                       |
| `--verbose`          | Print connection info and row count to stderr                                                                                                                                                                                                                                                                                                                                                           |

**Advanced — explicit overrides** (only when the user explicitly asks):

- `--host`, `--port`, `--database`, `--user`, `--password`, `--secure` — override individual env vars
- `--conn-string` — full connection URL, e.g. `http://user:pass@host:8123/db` (overrides everything)

These exist for one-off overrides. The standard workflow uses env vars.

## Examples

ClickHouse is a columnar analytical database — prefer aggregation and `LIMIT` over large scans.

### Schema inspection

```bash
# List all tables (skip system databases)
uv run scripts/query.py \
  "SELECT database, name, engine FROM system.tables WHERE database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema') ORDER BY database, name"

# Describe a table
uv run scripts/query.py \
  "SELECT name, type, position, default_kind FROM system.columns WHERE database = 'default' AND table = 'events' ORDER BY position"
```

### Ad-hoc queries

```bash
# Count rows
uv run scripts/query.py "SELECT count() FROM events"

# Recent records
uv run scripts/query.py \
  "SELECT event_id, created_at, event_type FROM events ORDER BY created_at DESC LIMIT 10" \
  --format table --verbose

# Aggregation over a time range
uv run scripts/query.py \
  "SELECT toDate(created_at) AS day, count() AS events FROM events WHERE created_at >= now() - INTERVAL 7 DAY GROUP BY day ORDER BY day" \
  --format csv
```

### Debug a slow query

```bash
# What's running right now
uv run scripts/query.py \
  "SELECT query_id, elapsed, query FROM system.processes ORDER BY elapsed DESC" \
  --format table

# Slow queries from the log (query_log must be enabled server-side)
uv run scripts/query.py \
  "SELECT query, query_duration_ms, read_rows FROM system.query_log WHERE type = 'QueryFinish' ORDER BY query_duration_ms DESC LIMIT 10" \
  --format table
```

## Safety

- **Query-shape validation (static, before connecting):** the script parses the input with sqlglot (ClickHouse dialect) and accepts only a single read-only `SELECT` — CTEs and set operations (`UNION`) are allowed, and anything inside a CTE must also be read-only. DML/DDL (`INSERT`, `UPDATE`/`ALTER TABLE … UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `OPTIMIZE`, …), `SHOW`, `DESCRIBE`, `GRANT`/`REVOKE` and other `Command` statements, transaction control, multi-statement input, and unparseable SQL are rejected with exit code 3 before a connection is ever made. `EXPLAIN` is intentionally unsupported — ClickHouse `EXPLAIN` does not execute the query (low value), and `EXPLAIN ANALYZE` does; debug via `system.processes` / `system.query_log` instead. Note: this is statement-level validation — it does not inspect function bodies; read-only side effects are limited by the denylist and the privilege gate below.
- **Side-effect denylist:** `INTO OUTFILE` (server-side file write), table functions with external I/O (`url`, `s3`, `file`, `remote`, `hdfs`, `mysql`, `postgresql`, `odbc`, `jdbc`, `sqlite`, …) and `sleep()`/`sleepEachRow()` are rejected.
- **Privilege gate (deterministic, no exceptions):** before every query the script runs `SHOW GRANTS` and rejects with exit code 3 — refusing the query — if the session user holds any grant other than direct `SELECT` grants (including `GRANT ALL`), holds role-based grants, or the grants cannot be verified. A privileged session never executes a query, even a read-only one. This also closes the `readonly = 2` gap: non-DML state changes such as `REVOKE` are rejected statically as `Command` statements.
- **Server-side read-only:** the script sets `SET readonly = 2` after the gate. `readonly` is a one-way ratchet — it cannot be lowered within the session. Persistent `INSERT`, `DELETE`, `ALTER`, `DROP`, `TRUNCATE`, `CREATE`, mutations, and other table writes are rejected by the server with error 164 (`READONLY`). Session settings and in-memory temporary tables remain available.
- **No hanging runs:** connections use a 10s connect timeout; the query runs under a server-side `max_execution_time` (`--timeout`, default 30s — auto-skipped when the server profile declares the setting READONLY, in which case the client read timeout and wall-clock deadline still bound the run), and the whole run (connect, privilege gate, query, transfer) is bounded by a wall-clock deadline of `--timeout` + 70s. `--timeout 0` disables all limits.
- **Exit codes:** 1 = connection/query errors and timeouts (descriptive messages with ClickHouse error codes, e.g. `164 READONLY`, `159 TIMEOUT_EXCEEDED`), 2 = missing dependency, 3 = validation/privilege rejection.
- Structured output goes to stdout only — diagnostics are always on stderr, so JSON/CSV output remains parseable.
