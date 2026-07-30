# /// script
# dependencies = [
#   "psycopg[binary]>=3.1,<4",
# ]
# requires-python = ">=3.10"
# ///

"""
Read-only PostgreSQL query executor.

Usage:
  uv run scripts/query.py [QUERY]

Connects using libpq environment variables (PGHOST, PGPORT, PGDATABASE, PGUSER)
and ~/.pgpass for authentication. No connection details in the command line.

Errors and diagnostics go to stderr. Results go to stdout.
"""

import argparse
import json
import os
import sys
import textwrap

try:
    import psycopg
except ImportError:
    print("Missing dependency: psycopg", file=sys.stderr)
    print("Run: uv run scripts/query.py ...", file=sys.stderr)
    sys.exit(2)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Execute a read-only PostgreSQL query.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              uv run scripts/query.py "SELECT * FROM users LIMIT 5"
              uv run scripts/query.py --file queries/slow.sql
              echo "SELECT 1" | uv run scripts/query.py
              uv run scripts/query.py "SELECT count(*) FROM orders" --format table
        """),
    )

    # Connection — only for explicit overrides. By default uses libpq env vars + .pgpass.
    parser.add_argument(
        "--conn-string", help="PostgreSQL connection URI (overrides all other settings)"
    )
    parser.add_argument("--host", help="Database host (default: $PGHOST or localhost)")
    parser.add_argument(
        "--port", type=int, help="Database port (default: $PGPORT or 5432)"
    )
    parser.add_argument(
        "--dbname", help="Database name (default: $PGDATABASE or $PGUSER or postgres)"
    )
    parser.add_argument(
        "--user", help="Database user (default: $PGUSER or current OS user)"
    )
    parser.add_argument("--password", help="Database password (use ~/.pgpass instead)")
    parser.add_argument(
        "--sslmode",
        help="SSL mode: prefer, require, verify-ca, verify-full (default: libpq default)",
    )

    # Query source
    parser.add_argument("query", nargs="?", help="SQL query string")
    parser.add_argument("--file", help="Read query from file (use - for stdin)")

    # Behaviour
    parser.add_argument(
        "--timeout", type=int, default=30, help="Query timeout in seconds (default: 30)"
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


def build_conninfo(args):
    """Build connection parameters from explicit args. Returns None to let libpq use env vars."""
    if args.conn_string:
        return args.conn_string

    conninfo = {}
    for key in ("host", "port", "dbname", "user", "password", "sslmode"):
        val = getattr(args, key)
        if val is not None:
            conninfo[key] = val

    return conninfo if conninfo else None


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
        elif hasattr(val, "isoformat"):
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
    conninfo = build_conninfo(args)
    query = get_query(args)

    if not query:
        print(
            "Error: no query provided. Pass query as argument, --file, or pipe to stdin.",
            file=sys.stderr,
        )
        print("Usage: uv run scripts/query.py [QUERY]", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        if conninfo is None:
            print(
                "Connecting via libpq environment variables (PGHOST, PGPORT, PGDATABASE, PGUSER) + ~/.pgpass",
                file=sys.stderr,
            )
        elif isinstance(conninfo, str):
            safe = conninfo.rsplit("@", 1)[-1] if "@" in conninfo else conninfo
            print(f"Connecting via URI: postgresql://...@{safe}", file=sys.stderr)
        else:
            safe = {k: v for k, v in conninfo.items() if k != "password"}
            print(f"Connecting with explicit params: {safe}", file=sys.stderr)

    try:
        conn = (
            psycopg.connect(conninfo, autocommit=True)
            if conninfo
            else psycopg.connect(autocommit=True)
        )
    except Exception as e:
        print(f"Error: connection failed — {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor()
    try:
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute(query, prepare=False, timeout=args.timeout)
    except Exception as e:
        print(f"Error: query failed — {e}", file=sys.stderr)
        cur.close()
        conn.close()
        sys.exit(1)

    columns = [desc.name for desc in cur.description] if cur.description else []
    rows = cur.fetchall()

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

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
