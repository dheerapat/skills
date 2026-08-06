# /// script
# dependencies = [
#   "clickhouse-connect>=1.6,<2",
#   "sqlglot>=25",
# ]
# requires-python = ">=3.10"
# ///

# type: ignore[ty:unresolved-import]
"""
Read-only ClickHouse query executor.

Usage:
  uv run scripts/query.py [QUERY]

Connects using CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_DATABASE,
CLICKHOUSE_USER, CLICKHOUSE_PASSWORD (and CLICKHOUSE_SECURE for TLS)
environment variables. No connection details in the command line.

Safety, before anything meaningful reaches the database:
  1. Static shape validation — sqlglot (ClickHouse dialect) accepts only a
     single read-only SELECT (CTEs and set operations allowed). DML/DDL,
     SHOW/GRANT/REVOKE/OPTIMIZE, DESCRIBE, EXPLAIN, multi-statement input and
     unparseable SQL are rejected with exit code 3.
  2. Side-effect denylist — INTO OUTFILE, table functions with external I/O
     (url, s3, file, remote, ...) and sleep()/sleepEachRow() are rejected.
  3. Privilege gate — SHOW GRANTS must show only direct SELECT grants for the
     session user; anything else (GRANT ALL, role grants, unverifiable) is
     rejected with exit code 3.

Server-side `SET readonly = 2` remains as defense-in-depth for persistent
table writes (error 164 READONLY).

Errors and diagnostics go to stderr. Results go to stdout.
"""

import argparse
import json
import logging
import os
import re
import signal
import sys
import textwrap

try:
    import clickhouse_connect
except ImportError:
    print("Missing dependency: clickhouse-connect", file=sys.stderr)
    print("Run: uv run scripts/query.py ...", file=sys.stderr)
    sys.exit(2)

try:
    import sqlglot
except ImportError:
    print("Missing dependency: sqlglot", file=sys.stderr)
    print("Run: uv run scripts/query.py ...", file=sys.stderr)
    sys.exit(2)

from sqlglot import exp
from sqlglot.errors import ParseError

# sqlglot warns ("contains unsupported syntax. Falling back to parsing as a
# 'Command'.") for statements we intentionally reject — the script reports its
# own rejection reason, so drop the noisy module-level warnings.
logging.getLogger("sqlglot").setLevel(logging.ERROR)

# Timeouts — a stuck connect/query must never stall the process indefinitely.
CONNECT_TIMEOUT = 10  # seconds — TCP/TLS/HTTP connect phase
_WALLCLOCK_MARGIN = 70  # seconds — buffer beyond the server-side max_execution_time


# Statement node types whose presence anywhere in the tree means it is not read-only.
_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Merge", "Upsert",
    "Create", "Alter", "Drop", "TruncateTable", "Truncate", "Optimize",
    "Set", "Command", "Call", "Kill", "Grant", "Revoke",
    "Refresh", "Move", "Rename", "Comment", "Attach", "Detach", "Check",
    "System", "Into", "Lock", "Copy", "Explain", "Describe",
]
_FORBIDDEN = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))

# Table functions that perform external I/O (network / server filesystem) or
# connect to other databases. ClickHouse parses them as Table nodes whose
# `this` is an Anonymous function call (regular tables are Identifiers).
_TABLE_FN_DENYLIST = {
    "url", "s3", "gcs", "file", "remote", "hdfs",
    "mysql", "postgresql", "odbc", "jdbc", "sqlite", "mongodb", "redis",
    "hudi", "iceberg", "deltalake", "azureblobstorage", "oss", "cosn",
}
# Functions with blocking or otherwise abusive side effects.
_FUNCTION_DENYLIST = {"sleep", "sleepeachrow"}

_INTO_OUTFILE_RE = re.compile(r"\bINTO\s+OUTFILE\b", re.IGNORECASE)

# Every SHOW GRANTS line must be a direct SELECT grant, optionally column-scoped.
_GRANT_RE = re.compile(
    r"(?i)^GRANT\s+SELECT(\s*\([^)]*\))?\s+ON\s+.+\s+TO\s+\S+"
    r"(\s+WITH\s+GRANT\s+OPTION)?\s*$"
)


def validate_read_only(sql):
    """Return None if sql is a single read-only SELECT (CTEs allowed), else an error string.

    EXPLAIN, SHOW, DESCRIBE, DML/DDL and multi-statement input are rejected.
    """
    if _INTO_OUTFILE_RE.search(sql):
        return "not read-only (INTO OUTFILE writes a file on the server)"

    try:
        statements = sqlglot.parse(sql, read="clickhouse")
    except ParseError as e:
        return f"unparseable SQL ({e})"

    if not statements:
        return "empty query"
    if len(statements) != 1:
        return "multiple statements are not allowed (single statement only)"

    stmt = statements[0]
    while isinstance(stmt, (exp.Paren, exp.Subquery)):  # unwrap bare parentheses
        stmt = stmt.this

    if not isinstance(stmt, (exp.Select, exp.With, exp.SetOperation)):
        return "not a SELECT query"

    for node in stmt.walk():
        if any(issubclass(node.__class__, klass) for klass in _FORBIDDEN):
            snippet = node.sql()[:120] or node.__class__.__name__
            return f"not read-only (found: {snippet})"
        if isinstance(node, exp.Table) and isinstance(node.this, exp.Anonymous):
            fn = str(node.this.this).lower()
            if fn in _TABLE_FN_DENYLIST:
                return f"not read-only (external I/O table function: {node.this.sql()[:120]})"
        elif isinstance(node, exp.Anonymous):
            fn = str(node.this).lower()
            if fn in _FUNCTION_DENYLIST:
                return f"not read-only (blocked function: {node.sql()[:120]})"

    return None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Execute a read-only ClickHouse query.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              uv run scripts/query.py "SELECT * FROM system.tables LIMIT 5"
              uv run scripts/query.py --file queries/slow.sql
              echo "SELECT 1" | uv run scripts/query.py
              uv run scripts/query.py "SELECT count(*) FROM orders" --format table
        """),
    )

    # Connection — only for explicit overrides. By default uses CLICKHOUSE_* env vars.
    parser.add_argument(
        "--conn-string", help="ClickHouse connection URL (overrides all other settings)"
    )
    parser.add_argument(
        "--host", help="Database host (default: $CLICKHOUSE_HOST or localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Database port (default: $CLICKHOUSE_PORT, 8123 or 8443)",
    )
    parser.add_argument(
        "--database",
        help="Database name (default: $CLICKHOUSE_DATABASE or server default)",
    )
    parser.add_argument(
        "--user", help="Database user (default: $CLICKHOUSE_USER or default)"
    )
    parser.add_argument(
        "--password", help="Database password (use $CLICKHOUSE_PASSWORD instead)"
    )
    parser.add_argument(
        "--secure",
        action="store_true",
        help="Enable HTTPS/TLS (default: $CLICKHOUSE_SECURE)",
    )

    # Query source
    parser.add_argument("query", nargs="?", help="SQL query string")
    parser.add_argument("--file", help="Read query from file (use - for stdin)")

    # Behaviour
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help=(
            "Server-side max_execution_time in seconds, 0 = unlimited (default: 30). "
            "Also bounds the whole run with a wall-clock deadline of --timeout + 70s."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "table"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print execution info to stderr"
    )
    parser.add_argument(
        "--check-privileges",
        action="store_true",
        help="Print the session user's grants and verify they are SELECT-only, then exit (0 = ok, 3 = rejected)",
    )

    return parser.parse_args(argv)


def env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def build_conn_kwargs(args):
    """Resolve connection kwargs from explicit args + CLICKHOUSE_* env vars.
    None leaves the driver default; a dict is passed to get_client()."""
    if args.conn_string:
        return {"dsn": args.conn_string}

    kwargs = {}

    host = args.host or os.environ.get("CLICKHOUSE_HOST")
    if host:
        kwargs["host"] = host

    port = args.port or os.environ.get("CLICKHOUSE_PORT")
    if port:
        kwargs["port"] = int(port)

    database = args.database or os.environ.get("CLICKHOUSE_DATABASE")
    if database:
        kwargs["database"] = database

    user = args.user or os.environ.get("CLICKHOUSE_USER")
    if user:
        kwargs["username"] = user

    password = args.password
    if password is None:
        password = os.environ.get("CLICKHOUSE_PASSWORD")
    if password:
        kwargs["password"] = password

    secure = args.secure or env_bool("CLICKHOUSE_SECURE")
    if secure:
        kwargs["secure"] = True

    return kwargs


def get_query(args):
    """Return the SQL query string from args, file, or stdin."""
    if args.file:
        if args.file == "-":
            return sys.stdin.read()
        with open(args.file) as f:
            return f.read()
    if args.query:
        return args.query
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def format_row(columns, row):
    """Serialize a row to a dict keyed by column name."""
    d = {}
    for col, val in zip(columns, row):
        if isinstance(val, (bytes, bytearray)):
            val = val.hex()
        elif hasattr(val, "isoformat"):  # date, datetime
            val = val.isoformat()
        d[col] = val
    return d


def format_csv(columns, rows, out):
    """Write rows as simple CSV."""
    import csv as csv_mod

    writer = csv_mod.writer(out)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)


def format_table(columns, rows, out):
    """Write a simple aligned table."""
    widths = [len(c) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header = "| " + " | ".join(c.ljust(w) for c, w in zip(columns, widths)) + " |"
    print(sep, file=out)
    print(header, file=out)
    print(sep.replace("-", "="), file=out)
    for row in rows:
        vals = [str(v).ljust(w) for v, w in zip(row, widths)]
        print("| " + " | ".join(vals) + " |", file=out)
    print(sep, file=out)


def fetch_grants(client):
    """Return (lines, error). lines is the session user's normalized SHOW GRANTS output."""
    try:
        result = client.command("SHOW GRANTS")
    except Exception as e:
        return [], f"SHOW GRANTS failed ({e})"
    if isinstance(result, str):
        raw = result.splitlines()
    else:
        raw = list(result)
    lines = [str(l).strip() for l in raw if str(l).strip()]
    return lines, None


def check_privileges(lines):
    """Return None if every grant is a direct SELECT grant, else an error string."""
    if not lines:
        return "cannot verify session privileges (SHOW GRANTS returned no grants)"
    for line in lines:
        if not _GRANT_RE.match(line):
            return f"session user has a non-SELECT grant: {line[:120]}"
    return None


def max_execution_time_settable(client):
    """Return True if max_execution_time is not a READONLY setting for this session.

    Some server profiles declare it READONLY (system.settings.readonly = 1) — passing
    it as a query setting then fails with error 164. On False (or an unreadable
    system.settings), the client-side read timeout and wall-clock deadline still
    bound the run.
    """
    try:
        row = client.command(
            "SELECT readonly FROM system.settings WHERE name = 'max_execution_time'"
        )
        return str(row).strip() == "0"
    except Exception:
        return False  # fail safe: rely on client-side + wall-clock timeouts


def _deadline(signum, frame):
    """SIGALRM handler — abort with a clear error instead of hanging."""
    raise TimeoutError(
        f"overall script deadline exceeded (timeout + {_WALLCLOCK_MARGIN}s buffer)"
    )


def main():
    args = parse_args()
    conn_kwargs = build_conn_kwargs(args)

    # Timeout wiring: server-side max_execution_time on the query (only when the
    # server allows the setting — probed after connecting), plus a client-side
    # read timeout and a wall-clock deadline both bounded to timeout + margin so
    # the server reports its own TIMEOUT_EXCEEDED where possible.
    deadline = None
    if args.timeout > 0:
        deadline = args.timeout + _WALLCLOCK_MARGIN
        if "dsn" not in conn_kwargs:
            conn_kwargs["connect_timeout"] = CONNECT_TIMEOUT
            conn_kwargs["send_receive_timeout"] = deadline

    query = get_query(args) if not args.check_privileges else None

    if not query and not args.check_privileges:
        print(
            "Error: no query provided. Pass query as argument, --file, or pipe to stdin.",
            file=sys.stderr,
        )
        print("Usage: uv run scripts/query.py [QUERY]", file=sys.stderr)
        sys.exit(1)

    # Static gate: the query must be a single read-only SELECT (CTEs allowed).
    # Runs before connecting, so nothing is ever sent to the server otherwise.
    if query:
        invalid = validate_read_only(query)
        if invalid:
            print(f"Error: query rejected — {invalid}", file=sys.stderr)
            print(
                "Only single read-only SELECT statements are allowed (CTEs are fine).",
                file=sys.stderr,
            )
            sys.exit(3)

    if args.verbose:
        if "dsn" in conn_kwargs:
            safe = str(conn_kwargs["dsn"]).rsplit("@", 1)[-1]
            print(f"Connecting via URL: clickhouse://...@{safe}", file=sys.stderr)
        else:
            host = conn_kwargs.get("host", "localhost")
            port = conn_kwargs.get(
                "port", "8443" if conn_kwargs.get("secure") else "8123"
            )
            user = conn_kwargs.get("username", "default")
            db = conn_kwargs.get("database", "server default")
            scheme = "https" if conn_kwargs.get("secure") else "http"
            print(
                f"Connecting to ClickHouse at {scheme}://{host}:{port} as {user} (database: {db})",
                file=sys.stderr,
            )

    # Wall-clock ceiling: a hung connect, unresponsive server, or stalled
    # result transfer must abort the process instead of hanging it.
    deadline_armed = False
    if deadline is not None:
        try:
            signal.signal(signal.SIGALRM, _deadline)
            signal.alarm(deadline)
            deadline_armed = True
        except (AttributeError, ValueError):
            pass  # non-POSIX platform — client timeouts still bound the run

    try:
        client = clickhouse_connect.get_client(**conn_kwargs)
    except Exception as e:
        print(f"Error: connection failed — {e}", file=sys.stderr)
        sys.exit(1)

    # Privilege gate: the session user must hold only direct SELECT grants.
    # Fail-closed — a privileged or unverifiable session never runs a query.
    if args.check_privileges:
        lines, err = fetch_grants(client)
        if err:
            print(f"Error: cannot verify session privileges — {err}", file=sys.stderr)
            client.close()
            sys.exit(3)
        for line in lines:
            print(line)
        bad = check_privileges(lines)
        if bad:
            print(f"Rejected: {bad}", file=sys.stderr)
            client.close()
            sys.exit(3)
        print("Session user is SELECT-only. Proceeding.", file=sys.stderr)
        client.close()
        sys.exit(0)

    lines, err = fetch_grants(client)
    bad = check_privileges(lines) if not err else err
    if bad:
        print(f"Error: query rejected — {bad}", file=sys.stderr)
        print("Use a dedicated SELECT-only user (see skill docs).", file=sys.stderr)
        client.close()
        sys.exit(3)
    if args.verbose:
        print("Session user is SELECT-only. Proceeding.", file=sys.stderr)

    # Server-side kill only when the setting is not READONLY for this session.
    query_settings = {}
    if args.timeout > 0 and max_execution_time_settable(client):
        query_settings["max_execution_time"] = args.timeout

    # Best-effort session setup: the server-side settings profile may already
    # enforce readonly=2 (in which case SET is rejected with 164 READONLY and we
    # keep going — the guard is already active).
    try:
        client.command("SET readonly = 2")
    except Exception as e:
        code = getattr(e, "code", None)
        if code != 164:
            print(f"Error: failed to set read-only mode — {e}", file=sys.stderr)
            client.close()
            sys.exit(1)

    try:
        result = client.query(query, settings=query_settings or None)
    except Exception as e:
        code = getattr(e, "code", None)
        name = getattr(e, "name", None)
        suffix = f" [{name}]" if name else ""
        print(f"Error: query failed (code {code}{suffix}) — {e}", file=sys.stderr)
        client.close()
        sys.exit(1)

    if deadline_armed:
        signal.alarm(0)  # connect + query are the hang risks; formatting is local CPU

    columns = list(result.column_names)
    rows = result.result_rows

    if args.verbose:
        print(f"Rows returned: {len(rows)}", file=sys.stderr)
        print(f"Columns: {columns}", file=sys.stderr)

    out = sys.stdout

    if args.format == "json":
        data = [format_row(columns, row) for row in rows]
        json.dump(data, out, default=str, indent=2)
        print(file=out)
    elif args.format == "csv":
        format_csv(columns, rows, out)
    elif args.format == "table":
        format_table(columns, rows, out)

    client.close()


if __name__ == "__main__":
    main()
