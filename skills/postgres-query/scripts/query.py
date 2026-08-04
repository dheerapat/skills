# /// script
# dependencies = [
#   "psycopg[binary]>=3.1,<4",
#   "sqlglot>=25",
# ]
# requires-python = ">=3.10"
# ///

# type: ignore[ty:unresolved-import]
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
import re
import sys
import textwrap

try:
    import psycopg
except ImportError:
    print("Missing dependency: psycopg", file=sys.stderr)
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


# Node types whose presence anywhere in the statement means it is not read-only.
_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Merge", "Upsert",
    "Create", "Alter", "Drop", "Truncate",
    "Copy", "Comment", "Grant", "Revoke",
    "Begin", "Commit", "Rollback", "Savepoint", "Release", "Transaction",
    "Set", "Call", "Vacuum", "Analyze", "Do", "Explain",
    "Prepare", "Execute", "Deallocate", "Reindex", "Import",
    "Cluster", "Checkpoint", "Declare", "Fetch", "Close",
    "Listen", "Notify", "Lock", "Refresh", "Command",
]
_FORBIDDEN = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))

_EXPLAIN_OPTIONS = {
    "ANALYZE", "VERBOSE", "COSTS", "BUFFERS", "TIMING", "SUMMARY", "SETTINGS", "WAL", "FORMAT",
}


def _strip_explain(sql):
    """If sql starts with EXPLAIN, return (True, inner_statement_text). Else (False, None).

    Handles both EXPLAIN forms: EXPLAIN (opt, ...) stmt and EXPLAIN [ANALYZE] [VERBOSE] stmt.
    """
    s = sql.lstrip()
    # strip leading comments before the EXPLAIN keyword
    while re.match(r"^/\*.*?\*/\s*|^--[^\n]*\n?\s*", s, re.S):
        s = re.sub(r"^(/\*.*?\*/|--[^\n]*\n?)\s*", "", s, count=1, flags=re.S)
    if not s.upper().startswith("EXPLAIN"):
        return False, None
    s = s[len("EXPLAIN"):].lstrip()

    if s.startswith("("):
        # consume the balanced option list, respecting string quotes
        depth, i = 0, 0
        in_single = in_double = False
        while i < len(s):
            c = s[i]
            if in_single:
                if c == "'" and (i == 0 or s[i - 1] != "\\"):
                    in_single = False
            elif in_double:
                if c == '"':
                    in_double = False
            elif c == "'":
                in_single = True
            elif c == '"':
                in_double = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        s = s[i:].lstrip()
    else:
        # consume the bare keyword form: ANALYZE / VERBOSE / ...
        while True:
            m = re.match(r"[A-Za-z_]+\b", s)
            if m and m.group(0).upper() in _EXPLAIN_OPTIONS:
                s = s[m.end():].lstrip()
            else:
                break

    return True, (s if s.strip() else None)


def validate_read_only(sql):
    """Return None if sql is a single read-only SELECT (CTEs allowed), else an error string.

    EXPLAIN/EXPLAIN ANALYZE is allowed when it wraps a read-only SELECT.
    """
    is_explain, inner = _strip_explain(sql)
    if is_explain:
        if inner is None:
            return "EXPLAIN given no statement"
        err = validate_read_only(inner)
        return f"EXPLAIN must wrap a read-only SELECT ({err})" if err else None

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except ParseError as e:
        return f"unparseable SQL ({e})"

    if not statements:
        return "empty query"
    if len(statements) != 1:
        return "multiple statements are not allowed (single statement only)"

    stmt = statements[0]
    while isinstance(stmt, exp.Paren):  # unwrap bare parentheses
        stmt = stmt.this

    if not isinstance(stmt, (exp.Select, exp.With, exp.SetOperation)):
        return "not a SELECT query"

    for node in stmt.walk():
        if any(issubclass(node.__class__, klass) for klass in _FORBIDDEN):
            snippet = node.sql()[:120] or node.__class__.__name__
            return f"not read-only (found: {snippet})"

    return None


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

    # Static gate: the query must be a single read-only SELECT (CTEs allowed).
    # Runs before connecting, so nothing is ever sent to the server otherwise.
    invalid = validate_read_only(query)
    if invalid:
        print(f"Error: query rejected — {invalid}", file=sys.stderr)
        print("Only single read-only SELECT statements are allowed (CTEs are fine).", file=sys.stderr)
        sys.exit(3)

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
            psycopg.connect(**conninfo)
            if isinstance(conninfo, dict)
            else psycopg.connect(conninfo or "")
        )
    except Exception as e:
        print(f"Error: connection failed — {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor()
    try:
        with conn.transaction():
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                (f"{args.timeout}s",),
            )

            # Privilege gate: reject the query unless the session role is a plain
            # (non-superuser, non-privileged) read-only role. Deterministic — no exceptions.
            cur.execute(
                "SELECT rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, rolreplication "
                "FROM pg_roles WHERE rolname = current_user"
            )
            priv_row = cur.fetchone()
            if priv_row is None:
                print(
                    "Error: query rejected — cannot verify session role in pg_roles.",
                    file=sys.stderr,
                )
                print("Use a dedicated SELECT-only role (see skill docs).", file=sys.stderr)
                sys.exit(3)
            elevated = [
                name
                for name, flag in zip(
                    ("rolsuper", "rolcreaterole", "rolcreatedb", "rolbypassrls", "rolreplication"),
                    priv_row,
                )
                if flag
            ]
            if elevated:
                print(
                    f"Error: query rejected — session user has elevated privileges ({', '.join(elevated)}).",
                    file=sys.stderr,
                )
                print("Use a dedicated SELECT-only role (see skill docs).", file=sys.stderr)
                sys.exit(3)

            # Extended protocol rejects multiple statements, preventing COMMIT/ROLLBACK escapes.
            cur.execute(query, prepare=True)
            columns = [desc.name for desc in cur.description] if cur.description else []
            rows = cur.fetchall()
    except Exception as e:
        print(f"Error: query failed — {e}", file=sys.stderr)
        cur.close()
        conn.close()
        sys.exit(1)

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
