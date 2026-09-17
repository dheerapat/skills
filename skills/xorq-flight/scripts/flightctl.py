# /// script
# dependencies = ["pyarrow>=17", "cloudpickle>=3"]
# requires-python = ">=3.10"
# ///

# type: ignore[ty:unresolved-import]
"""
Read-only client for a Xorq Arrow Flight (gRPC) server.

Usage:
  uv run scripts/flightctl.py exchanges
  uv run scripts/flightctl.py describe double_it
  uv run scripts/flightctl.py run double_it --input data.parquet

Speaks the Flight action protocol directly with pyarrow — no xorq install
needed on the client. Only discovery actions and `do_exchange` are used;
`do_put`, `add-exchange`, `drop_table`, `drop_view`, and `read_parquet`
are never called, so the server's state is never mutated.

Target selection:
  --url grpc://host:port   or   --host / --port
  env: XORQ_FLIGHT_URL  or  XORQ_FLIGHT_HOST + XORQ_FLIGHT_PORT
"""

import argparse
import json
import os
import re
import signal
import sys
import textwrap
from urllib.parse import urlparse

try:
    import pyarrow as pa
    import pyarrow.csv as pa_csv
    import pyarrow.flight as paf
    import pyarrow.parquet as pa_parquet
    from cloudpickle import dumps, loads
except ImportError:
    print("Missing dependency: pyarrow / cloudpickle", file=sys.stderr)
    print("Run: uv run scripts/flightctl.py ...", file=sys.stderr)
    sys.exit(2)

COMMANDS = ("health", "info", "exchanges", "actions", "tables", "schema", "describe", "run")
DEFAULT_PORT = 8815
_WALLCLOCK_MARGIN = 30  # seconds — buffer beyond --timeout for startup/teardown

# Exchange/table names go into Flight descriptors, not a shell: reject anything
# that isn't a plain identifier-ish token anyway.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@:-]{0,127}$")


def die(msg, code):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def _deadline(signum, frame):
    raise TimeoutError(f"wall-clock deadline exceeded (--timeout + {_WALLCLOCK_MARGIN}s)")


def resolve_url(args):
    url = args.url or os.environ.get("XORQ_FLIGHT_URL")
    if url:
        parsed = urlparse(url if "://" in url else f"grpc://{url}")
        if parsed.scheme not in ("grpc", "grpc+tls"):
            die(f"unsupported scheme {parsed.scheme!r} — use grpc:// or grpc+tls://", 2)
        return f"{parsed.scheme}://{parsed.hostname}:{parsed.port or DEFAULT_PORT}"
    host = args.host or os.environ.get("XORQ_FLIGHT_HOST", "localhost")
    port = args.port or os.environ.get("XORQ_FLIGHT_PORT", DEFAULT_PORT)
    return f"grpc://{host}:{port}"


def call_action(client, name, payload=None):
    """Invoke a Flight action; request/response bodies are cloudpickle."""
    body = dumps(payload) if payload is not None else b""
    (result,) = client.do_action(paf.Action(name, body))
    return loads(result.body.to_pybytes())


def read_input(path, required_schema=None):
    """Load the input table for an exchange from parquet/CSV/Arrow-IPC-stdin."""
    if path is None or path == "-":
        if required_schema is None:
            die("--input is required: no schema available on the server to fall back to", 2)
        return pa.Table.from_batches([], schema=required_schema)
    if path.endswith(".parquet"):
        return pa_parquet.read_table(path)
    if path.endswith(".csv"):
        return pa_csv.read_csv(path)
    die(f"unsupported input {path!r} — use .parquet or .csv", 2)


def do_exchange(client, command, table):
    """Stream `table` through an exchange and return the result table.

    Mirrors xorq's own client: begin(schema) -> write batches -> done_writing(),
    with reads draining concurrently (a sequential read deadlocks).
    """
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue

    batches = list(table.to_batches())
    queue = Queue()

    def do_writes(writer):
        writer.begin(table.schema)
        for batch in batches:
            writer.write_batch(batch)
        writer.done_writing()

    def do_reads(reader):
        try:
            for chunk in reader:
                if chunk.data:
                    queue.put(chunk.data)
        except BaseException as e:  # noqa: BLE001 — surfaced to the caller below
            queue.put(e)
        finally:
            queue.put(None)

    writer, reader = client.do_exchange(paf.FlightDescriptor.for_command(command))
    with writer:
        with ThreadPoolExecutor(max_workers=2) as pool:
            writes = pool.submit(do_writes, writer)
            reads = pool.submit(do_reads, reader)
            writes.result()
            reads.result()

    out = []
    while (value := queue.get()) is not None:
        if isinstance(value, BaseException):
            raise value
        out.append(value)
    return pa.Table.from_batches(out) if out else pa.Table.from_batches([], schema=table.schema)


def emit(table, fmt, output=None):
    if fmt in ("arrow", "parquet"):
        if not output:
            die(f"--format {fmt} writes binary — pass --output FILE", 2)
        if fmt == "arrow":
            with pa.OSFile(output, "wb") as fh, pa.ipc.new_file(fh, table.schema) as w:
                w.write_table(table)
        else:
            pa_parquet.write_table(table, output)
        print(f"Wrote {table.num_rows} rows to {output}", file=sys.stderr)
        return
    if fmt == "json":
        json.dump(table.to_pylist(), sys.stdout, default=str, indent=2)
        print(file=sys.stdout)
    else:
        import csv as csv_mod

        writer = csv_mod.writer(sys.stdout)
        writer.writerow(table.column_names)
        for row in zip(*(table.column(i).to_pylist() for i in range(table.num_columns))):
            writer.writerow(row)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only client for a Xorq Arrow Flight server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              uv run scripts/flightctl.py exchanges
              uv run scripts/flightctl.py describe score_sentiment
              uv run scripts/flightctl.py run score_sentiment --input titles.csv
              uv run scripts/flightctl.py run marts/monthly --format csv --limit 20
        """),
    )
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("name", nargs="?", help="Exchange or table name (describe/schema/run)")

    parser.add_argument("--url", help="grpc://host:port (default: $XORQ_FLIGHT_URL)")
    parser.add_argument("--host", help="Server host (default: $XORQ_FLIGHT_HOST or localhost)")
    parser.add_argument("--port", help="Server port (default: $XORQ_FLIGHT_PORT or 8815)")

    parser.add_argument(
        "-i", "--input", help="Input file for `run` (.parquet / .csv); omit if the exchange takes no input"
    )
    parser.add_argument(
        "-f", "--format", choices=("json", "csv", "arrow", "parquet"), default="json",
        help="Output format for `run` (default: json)",
    )
    parser.add_argument("-o", "--output", help="Output file for --format arrow/parquet")
    parser.add_argument("--limit", type=int, help="Truncate `run` output to N rows")
    parser.add_argument("--timeout", type=int, default=60, help="Wall-clock budget in seconds (default: 60)")
    parser.add_argument("--verbose", action="store_true", help="Print the target URL to stderr")
    return parser.parse_args(argv)


def main():
    args = parse_args()

    if args.command in ("describe", "schema", "run") and not args.name:
        die(f"`{args.command}` requires a name", 2)
    if args.name and not NAME_RE.match(args.name):
        die(f"invalid name: {args.name!r}", 3)

    url = resolve_url(args)
    if args.verbose:
        print(f"target: {url}", file=sys.stderr)

    deadline_armed = False
    try:
        signal.signal(signal.SIGALRM, _deadline)
        signal.alarm(args.timeout + _WALLCLOCK_MARGIN)
        deadline_armed = True
    except (AttributeError, ValueError):
        pass

    try:
        client = paf.FlightClient(url)
        # Fail fast with a clear message instead of a gRPC timeout.
        call_action(client, "healthcheck")

        if args.command == "health":
            print("ok")
        elif args.command == "info":
            exchanges = call_action(client, "list-exchanges")
            print(f"url:        {url}")
            print(f"version:    {call_action(client, 'version')}")
            print(f"exchanges:  {len(exchanges)}")
            print(f"tables:     {len(call_action(client, 'list_tables', {}))}")
        elif args.command == "exchanges":
            for name in call_action(client, "list-exchanges"):
                print(name)
        elif args.command == "actions":
            for name in call_action(client, "list-actions"):
                print(name)
        elif args.command == "tables":
            for name in call_action(client, "list_tables", {}):
                print(name)
        elif args.command == "schema":
            schema = call_action(client, "table_info", {"table_name": args.name})
            print(schema)
        elif args.command == "describe":
            meta = call_action(client, "query-exchange", args.name)
            if meta is None:
                die(f"no exchange named {args.name!r}", 1)
            json.dump(meta, sys.stdout, default=str, indent=2)
            print(file=sys.stdout)
        elif args.command == "run":
            if args.input:
                # The file carries its own schema — no need to ask the server.
                table = read_input(args.input)
            else:
                meta = call_action(client, "query-exchange", args.name)
                if meta is None:
                    die(f"no exchange named {args.name!r}", 1)
                required = meta.get("schema-in-required")
                if required is None:
                    die(f"exchange {args.name!r} declares no input schema — pass --input", 2)
                table = pa.Table.from_batches([], schema=required.to_pyarrow())
            result = do_exchange(client, args.name.encode(), table)
            if args.limit is not None:
                result = result.slice(0, args.limit)
            emit(result, args.format, args.output)
    except ModuleNotFoundError as e:
        # Server-side schema objects unpickle into xorq's vendored ibis.
        die(f"{e} — this response needs xorq: rerun as "
            f"`uv run --with xorq scripts/flightctl.py ...`", 1)
    except TimeoutError as e:
        die(str(e), 1)
    except (paf.FlightUnavailableError, OSError) as e:
        die(f"cannot reach Flight server at {url} — {e}", 1)
    except paf.FlightError as e:
        die(f"server error — {e}", 1)
    finally:
        if deadline_armed:
            signal.alarm(0)


if __name__ == "__main__":
    main()
