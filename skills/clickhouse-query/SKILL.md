---
name: clickhouse-query
description: Run read-only SQL queries against ClickHouse databases. Connect via CLICKHOUSE_* environment variables — no connection details exposed to the agent.
---

# ClickHouse Query Skill

Run read-only queries against a ClickHouse database. The bundled script uses [clickhouse-connect](https://clickhouse.com/docs/integrations/language-clients/python) over the HTTP interface with server-side read-only enforcement (`SET readonly = 2`) — writes are rejected by the database with error 164 (`READONLY`).

**Connection details are never known to the agent.** The user configures `CLICKHOUSE_*` environment variables before starting the agent session. The agent references `$CLICKHOUSE_HOST` etc. in commands — bash expands them at runtime, the literal values never enter the agent's context.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager) — installs dependencies automatically
- Python 3.10+
- Network access to the ClickHouse HTTP port (8123 plain, 8443 TLS)

## Setup — one-time by the user

Before using this skill, the user must configure the connection **outside the agent session**:

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

### Check that the connection is configured

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

## Available script

| Script             | Description                                              |
| ------------------ | -------------------------------------------------------- |
| `scripts/query.py` | Execute a read-only SQL query, results as JSON/CSV/table |

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

| Flag            | Description                                             |
| --------------- | ------------------------------------------------------- |
| `--timeout SEC` | Query timeout in seconds (default: 30, `0` = unlimited) |
| `--verbose`     | Print connection info and row count to stderr           |

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

- The script sets `SET readonly = 2` immediately after connecting. `readonly` is a one-way ratchet — it cannot be lowered within the session. Persistent `INSERT`, `DELETE`, `ALTER`, `DROP`, `TRUNCATE`, `CREATE`, mutations, and other table writes are rejected by the server with error 164 (`READONLY`). Session settings and in-memory temporary tables remain available.
- This is a persistent-data guard, not a security boundary for admin credentials. ClickHouse permits some non-DML state changes in read-only mode (for example, `REVOKE`). Privileged functions and external integrations may also have side effects. Use a dedicated `SELECT`-only user and a server-side read-only profile when untrusted queries or a strong read-only guarantee are involved.
- The `--timeout` is applied as a server-side `max_execution_time` session limit before enabling read-only.
- Connection errors, query errors, and timeouts print descriptive messages (with ClickHouse error code, e.g. `164 READONLY`, `159 TIMEOUT_EXCEEDED`) to stderr and exit with code 1.
- Structured output goes to stdout only — diagnostics are always on stderr, so JSON/CSV output remains parseable.
