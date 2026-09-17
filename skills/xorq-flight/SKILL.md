---
name: xorq-flight
description: Talk to a running Xorq Arrow Flight (gRPC) server — list the exchanges it hosts, inspect them, and run them by streaming data in and getting Arrow results back. Read-only client: no do_put, no schema or exchange mutation. Use when work should go through a hosted Xorq pipeline instead of local code.
---

# Xorq Flight Skill

Drive a running [Xorq](https://xorq.dev) Arrow Flight server. A Flight server hosts **exchanges** — named computations (unbound expressions, UDFs, UDTFs, models) that accept Arrow record batches and stream Arrow results back over gRPC.

**Prefer an existing exchange over writing new code.** An exchange is versioned, pinned, and already running; a locally written query is none of those. If no exchange matches the task, say so rather than approximating with a similar-sounding one.

**The client is read-only.** It uses only `healthcheck`, `version`, `list-actions`, `list-exchanges`, `query-exchange`, `list_tables`, `table_info`, and `do_exchange`. `do_put`, `add-exchange`, `add-action`, `drop_table`, `drop_view`, and `read_parquet` are never called, so server state is never mutated.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- A reachable Xorq Flight server, for example:
  ```bash
  xorq serve-unbound builds/<hash> --host 0.0.0.0 --port 8815
  xorq serve-flight-udxf builds/<udxf-hash> --port 8080
  xorq catalog serve-unbound my-entry --port 8815
  ```
  or any server built with `xorq.flight.FlightServer`.

## Setup — one-time by the user

Point the skill at the server:

```bash
export XORQ_FLIGHT_URL=grpc://my-host:8815
# or
export XORQ_FLIGHT_HOST=my-host
export XORQ_FLIGHT_PORT=8815
```

Defaults when unset: `grpc://localhost:8815`. `--url` / `--host` / `--port` override the env vars per call.

## What the agent does

### 1. Confirm the server is up

```bash
uv run scripts/flightctl.py health
uv run scripts/flightctl.py info        # version, exchange count, table count
```

If this fails with "cannot reach Flight server", report it — the server is not running or the URL is wrong. Do not guess ports.

### 2. Discover what is hosted

```bash
uv run scripts/flightctl.py exchanges
uv run scripts/flightctl.py exchanges | grep -i score
```

Exchange names are the **entire** discovery surface — there is no description index. Try partial greps before concluding something doesn't exist. Servers also register a `default` alias for the last added exchange.

### 3. Inspect (optional)

```bash
uv run scripts/flightctl.py describe double_it
```

Prints the exchange's declared input schema, output schema, and description. **Requires `xorq` importable in the environment** — the server returns ibis schema objects, which unpickle into xorq's vendored ibis. Without xorq you get:

```
Error: No module named 'xorq' — this response needs xorq: rerun as `uv run --with xorq scripts/flightctl.py ...`
```

Cheaper alternative when xorq isn't available: run the exchange on a tiny input and read the output shape.

```bash
uv run scripts/flightctl.py run double_it --input sample.csv --limit 1
```

### 4. Run

```bash
uv run scripts/flightctl.py run double_it --input data.csv
uv run scripts/flightctl.py run double_it --input data.parquet -f csv --limit 20
uv run scripts/flightctl.py run double_it --input data.parquet -f parquet -o out.parquet
```

Results go to **stdout** for `json`/`csv`; anything the script prints for humans goes to **stderr**, so stdout stays parseable.

`--input` accepts `.parquet` and `.csv`. Omit it only when the exchange declares an input schema — otherwise the script exits 2 and tells you to pass `--input`.

### 5. Report

State which exchange produced the result and what input you streamed. If no exchange matched, say so explicitly.

## Available script

| Script                | Description                                                                          |
| --------------------- | ------------------------------------------------------------------------------------ |
| `scripts/flightctl.py`| Read-only Xorq Flight client: `health` / `info` / `exchanges` / `actions` / `tables` / `schema` / `describe` / `run` |

PEP 723 inline metadata, dependencies `pyarrow` + `cloudpickle` only — `uv run` installs them on demand. **xorq itself is not needed on the client** (except for `describe` / `schema`, see above).

## Usage

```bash
uv run scripts/flightctl.py COMMAND [NAME] [OPTIONS]
```

| Command     | Needs name | Output                                                   |
| ----------- | ---------- | -------------------------------------------------------- |
| `health`    | no         | `ok`                                                     |
| `info`      | no         | URL, server version, exchange count, table count         |
| `exchanges` | no         | One exchange name per line — pipe to `grep`              |
| `actions`   | no         | Action names the server exposes                          |
| `tables`    | no         | Table names on the server                                |
| `schema`    | yes        | A table's schema (needs xorq importable)                 |
| `describe`  | yes        | An exchange's input/output schema + description (needs xorq) |
| `run`       | yes        | Result rows on stdout                                    |

### Options

| Flag             | Description                                                              |
| ---------------- | ------------------------------------------------------------------------ |
| `-i`, `--input`  | Input file for `run`: `.parquet` or `.csv`                               |
| `-f`, `--format` | `run` output: `json` (default), `csv`, `arrow`, `parquet`                |
| `-o`, `--output` | Output file — required for `--format arrow`/`parquet` (binary)           |
| `--limit N`      | Truncate `run` output to N rows                                          |
| `--url`          | `grpc://host:port` or `grpc+tls://host:port`                             |
| `--host`/`--port`| Override host / port (default 8815)                                      |
| `--timeout SEC`  | Wall-clock budget (default 60)                                           |
| `--verbose`      | Print the resolved server URL to stderr                                  |

## Examples

### Find and run a hosted transform

```bash
uv run scripts/flightctl.py exchanges | grep -i score
uv run scripts/flightctl.py run score_sentiment --input titles.csv -f csv
```

### Learn an exchange's output shape cheaply

```bash
printf 'a\n1\n' > /tmp/one.csv
uv run scripts/flightctl.py run double_it --input /tmp/one.csv
```

### Persist a large result

```bash
uv run scripts/flightctl.py run marts/monthly --input events.parquet -f parquet -o monthly.parquet
```

### Check what a server exposes

```bash
uv run scripts/flightctl.py info
uv run scripts/flightctl.py actions
uv run scripts/flightctl.py tables
```

## Safety

- **Read-only protocol surface:** only listing/querying actions and `do_exchange` are used. Mutating actions (`add-exchange`, `add-action`, `drop_table`, `drop_view`, `read_parquet`) and `do_put` are not implemented — there is no code path to them.
- **Input validation:** names must match `^[A-Za-z0-9][A-Za-z0-9._/@:-]{0,127}$`; anything else is rejected with exit code 3 before a connection is made. Names go into Flight descriptors as an argv-style byte payload, never through a shell.
- **No hanging runs:** a wall-clock alarm (`--timeout` + 30s) aborts a stuck server, a stalled exchange, or a slow transfer with exit code 1. Unreachable servers fail fast with a clear message instead of a gRPC timeout.
- **Results vs diagnostics:** results go to stdout; row counts, file writes, and the resolved URL go to stderr, so `-f json` / `-f csv` output stays parseable.
- **Server-side effects:** `do_exchange` executes the exchange — that is its purpose — but it writes nothing back to the server's tables or exchange registry.

## Exit codes

| Code | Meaning                                                             |
| ---- | ------------------------------------------------------------------- |
| 0    | Success                                                             |
| 1    | Server unreachable, server error, or response needs `xorq` installed |
| 2    | Usage error (missing name, missing `--input`, binary format without `-o`) |
| 3    | Input rejected — invalid exchange/table name                        |
