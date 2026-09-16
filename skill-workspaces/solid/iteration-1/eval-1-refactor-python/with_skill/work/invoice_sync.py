"""Nightly invoice sync.

The job's one reason to change: *what the sync does*, and in what order.
`sync_invoices` is the pure orchestration and takes its collaborators;
`run_invoice_sync` is the edge that builds the real ones.
"""
from collections.abc import Callable

from invoice_formatting import COLUMNS, render
from invoice_mail import InvoiceMailer
from invoice_repository import InvoiceRepository, connect

DSN = "host=prod user=svc password=hunter2 dbname=billing"

# All the sync needs from "delivery": take the payload, raise if it failed.
Notifier = Callable[[str], None]


def sync_invoices(repo: InvoiceRepository, notify: Notifier,
                  fmt: str = "csv", dry_run: bool = False) -> int:
    rows = repo.overdue(COLUMNS)
    payload = render(rows, fmt)
    if not dry_run:
        notify(payload)
        repo.mark_synced()
    print(f"synced {len(rows)} invoices as {fmt}")
    return len(rows)


def run_invoice_sync(fmt: str = "csv", dry_run: bool = False, dsn: str = DSN) -> int:
    """Wire up the real collaborators and run the job."""
    conn = connect(dsn)
    try:
        return sync_invoices(InvoiceRepository(conn), InvoiceMailer().send, fmt, dry_run)
    finally:
        conn.close()
