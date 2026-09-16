"""Render invoice rows into the report payload.

One reason to change: what the report looks like. Adding a format means adding
a function and one FORMATTERS entry below — no existing branch is edited.
"""
import csv
import io
import json

# The report's columns, also the SELECT list the repository asks for.
COLUMNS = ["id", "vendor", "amount", "currency", "issued_at"]


def _csv(rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(COLUMNS)
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


def _tsv(rows):
    return "\n".join("\t".join(str(c) for c in r) for r in rows)


def _json(rows):
    return json.dumps([dict(zip(COLUMNS, r)) for r in rows], default=str)


# csv is deliberately not "_tsv with a different delimiter": csv.writer quotes
# fields, uses \r\n line endings, and renders NULL as empty instead of "None".
FORMATTERS = {"csv": _csv, "tsv": _tsv, "json": _json}


def render(rows, fmt):
    """Rows -> payload text. Raises ValueError for an unknown format."""
    try:
        formatter = FORMATTERS[fmt]
    except KeyError:
        raise ValueError("unsupported format") from None
    return formatter(rows)
