"""Nightly invoice sync.

The old `InvoiceSyncManager` owned SQL, formatting, SMTP and stdout at once.
Split by responsibility; behaviour is unchanged:

  InvoiceRepository      -> Postgres (SELECT overdue / UPDATE synced)   [S]
  InvoiceReporter        -> payload format, one class per format        [O/L]
  InvoiceMailSender      -> delivery only                               [S]
  InvoiceSyncManager     -> orchestration, depends on the protocols     [I/D]

`run(fmt, dry_run)` keeps its signature, its `ValueError("unsupported
format")`, its stdout line and its return value.
"""
from __future__ import annotations

import csv
import io
import json
import smtplib
from typing import Callable, Protocol, Sequence

import psycopg2

DSN = "host=prod user=svc password=hunter2 dbname=billing"

COLUMNS = ["id", "vendor", "amount", "currency", "issued_at"]

SELECT_OVERDUE = (
    "SELECT id, vendor, amount, currency, issued_at FROM invoices "
    "WHERE status = 'OPEN' AND issued_at < now() - interval '30 days'"
)
UPDATE_SYNCED = "UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'"

Row = Sequence[object]
Rows = Sequence[Row]


# --------------------------------------------------------------------------
# S: data access lives here and nowhere else
# --------------------------------------------------------------------------
class InvoiceRepository(Protocol):
    """The only two things anyone needs from storage."""

    def fetch_overdue(self) -> Rows: ...

    def mark_synced(self) -> None: ...


class PostgresInvoiceRepository:
    def __init__(
        self,
        dsn: str = DSN,
        connect: Callable[..., object] = psycopg2.connect,
    ) -> None:
        self._conn = connect(dsn)

    def fetch_overdue(self) -> Rows:
        cur = self._conn.cursor()
        cur.execute(SELECT_OVERDUE)
        return cur.fetchall()

    def mark_synced(self) -> None:
        cur = self._conn.cursor()
        cur.execute(UPDATE_SYNCED)
        self._conn.commit()


# --------------------------------------------------------------------------
# O: new format == new class. No existing class or if-chain is edited.
# L: every reporter honours the full contract - none raises for a valid call.
# --------------------------------------------------------------------------
class InvoiceReporter(Protocol):
    def export(self, rows: Rows) -> str: ...


class CsvReporter:
    format = "csv"

    def export(self, rows: Rows) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()


class TsvReporter:
    format = "tsv"

    def export(self, rows: Rows) -> str:
        return "\n".join("\t".join(str(c) for c in row) for row in rows)


class JsonReporter:
    format = "json"

    def export(self, rows: Rows) -> str:
        return json.dumps(
            [dict(zip(COLUMNS, row)) for row in rows], default=str
        )


class ReporterRegistry:
    """Looks up a reporter by format name."""

    def __init__(self, reporters: Sequence[InvoiceReporter] = ()) -> None:
        self._by_format = {r.format: r for r in reporters}

    def register(self, reporter: InvoiceReporter) -> None:
        self._by_format[reporter.format] = reporter

    def for_format(self, fmt: str) -> InvoiceReporter:
        try:
            return self._by_format[fmt]
        except KeyError:
            raise ValueError("unsupported format") from None


def default_reporters() -> ReporterRegistry:
    return ReporterRegistry([CsvReporter(), TsvReporter(), JsonReporter()])


# --------------------------------------------------------------------------
# S: delivery. Knows nothing about SQL or formats.
# --------------------------------------------------------------------------
class InvoiceMailSender(Protocol):
    def send(self, payload: str) -> None: ...


class SmtpInvoiceMailSender:
    def __init__(
        self,
        host: str = "mail.internal",
        port: int = 587,
        account: str = "ops@corp",
        password: str = "apassword",
        sender: str = "ops@corp",
        recipients: Sequence[str] = ("finance@corp",),
        subject: str = "overdue invoices",
    ) -> None:
        self._host = host
        self._port = port
        self._account = account
        self._password = password
        self._sender = sender
        self._recipients = list(recipients)
        self._subject = subject

    def send(self, payload: str) -> None:
        with smtplib.SMTP(self._host, self._port) as session:
            session.starttls()
            session.login(self._account, self._password)
            session.sendmail(
                self._sender,
                self._recipients,
                f"Subject: {self._subject}\n\n{payload}",
            )


# --------------------------------------------------------------------------
# Orchestration. Every collaborator is an injected abstraction [D]; each one
# is declared with only the methods this class actually calls [I].
# --------------------------------------------------------------------------
class InvoiceSyncManager:
    def __init__(
        self,
        repository: InvoiceRepository | None = None,
        reporters: ReporterRegistry | None = None,
        mailer: InvoiceMailSender | None = None,
        printer: Callable[[str], object] = print,
    ) -> None:
        self._repository = repository or PostgresInvoiceRepository()
        self._reporters = reporters or default_reporters()
        self._mailer = mailer or SmtpInvoiceMailSender()
        self._print = printer

    def run(self, fmt: str = "csv", dry_run: bool = False) -> int:
        rows = self._repository.fetch_overdue()
        payload = self._reporters.for_format(fmt).export(rows)

        if not dry_run:
            self._mailer.send(payload)
            self._repository.mark_synced()

        self._print(f"synced {len(rows)} invoices as {fmt}")
        return len(rows)
