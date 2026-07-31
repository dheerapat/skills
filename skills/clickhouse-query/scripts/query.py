# /// script
# dependencies = [
#   "clickhouse-connect>=1.6,<2",
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

Enforces persistent-data read-only mode server-side with `SET readonly = 2`
right after connecting. Persistent DDL, DML, and setting downgrade attempts
are rejected by the server with error 164 (READONLY).

Errors and diagnostics go to stderr. Results go to stdout.
"""

import argparse
import json
import os
import sys
import textwrap

try:
    import clickhouse_connect
except ImportError:
    print("Missing dependency: clickhouse-connect", file=sys.stderr)
    print("Run: uv run scripts/query.py ...", file=sys.stderr)
    sys.exit(2)


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
        help="Query timeout in seconds, 0 = unlimited (default: 30)",
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


def main():
    args = parse_args()
    conn_kwargs = build_conn_kwargs(args)
    query = get_query(args)

    if not query:
        print(
            "Error: no query provided. Pass query as argument, --file, or pipe to stdin.",
            file=sys.stderr,
        )
        print("Usage: uv run scripts/query.py [QUERY]", file=sys.stderr)
        sys.exit(1)

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

    try:
        client = clickhouse_connect.get_client(**conn_kwargs)
    except Exception as e:
        print(f"Error: connection failed — {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Session-level execution timeout BEFORE readonly (per-query settings are
        # rejected under readonly=2). 0 = unlimited.
        if args.timeout > 0:
            client.command(f"SET max_execution_time = {args.timeout}")
        # Server-side read-only enforcement: writes fail with error 164 (READONLY).
        client.command("SET readonly = 2")
    except Exception as e:
        print(f"Error: failed to set read-only mode — {e}", file=sys.stderr)
        client.close()
        sys.exit(1)

    try:
        result = client.query(query)
    except Exception as e:
        code = getattr(e, "code", None)
        name = getattr(e, "name", None)
        suffix = f" [{name}]" if name else ""
        print(f"Error: query failed (code {code}{suffix}) — {e}", file=sys.stderr)
        client.close()
        sys.exit(1)

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
