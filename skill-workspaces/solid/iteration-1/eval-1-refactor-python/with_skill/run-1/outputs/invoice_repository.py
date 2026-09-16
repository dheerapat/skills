"""Invoice SQL. One reason to change: the database (schema, queries, driver)."""


class InvoiceRepository:
    """Overdue-invoice reads and the status flip. Holds a DB connection."""

    def __init__(self, conn):
        self.conn = conn

    def overdue(self, columns):
        """Rows with status OPEN and issued more than 30 days ago."""
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT {', '.join(columns)} FROM invoices "
            "WHERE status = 'OPEN' AND issued_at < now() - interval '30 days'"
        )
        return cur.fetchall()

    def mark_synced(self):
        """Flip every OPEN invoice to SYNCED and commit."""
        cur = self.conn.cursor()
        cur.execute("UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'")
        self.conn.commit()


def connect(dsn):
    """Open the real connection. The only place psycopg2 is known.

    Imported lazily so the rest of this module — and everything that imports
    it — stays usable without the driver installed.
    """
    import psycopg2

    return psycopg2.connect(dsn)
