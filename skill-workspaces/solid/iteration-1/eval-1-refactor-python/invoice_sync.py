"""Nightly invoice sync. One file, one class, everything in it."""
import smtplib
import csv
import io
import psycopg2

DSN = "host=prod user=svc password=hunter2 dbname=billing"


class InvoiceSyncManager:
    def __init__(self):
        self.conn = psycopg2.connect(DSN)

    def run(self, fmt="csv", dry_run=False):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, vendor, amount, currency, issued_at FROM invoices "
            "WHERE status = 'OPEN' AND issued_at < now() - interval '30 days'"
        )
        rows = cur.fetchall()

        if fmt == "csv":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["id", "vendor", "amount", "currency", "issued_at"])
            for r in rows:
                w.writerow(r)
            payload = buf.getvalue()
        elif fmt == "tsv":
            payload = "\n".join("\t".join(str(c) for c in r) for r in rows)
        elif fmt == "json":
            import json
            payload = json.dumps(
                [dict(zip(["id", "vendor", "amount", "currency", "issued_at"], r), )
                 for r in rows], default=str)
        else:
            raise ValueError("unsupported format")

        if not dry_run:
            with smtplib.SMTP("mail.internal", 587) as s:
                s.starttls()
                s.login("ops@corp", "apassword")
                s.sendmail(
                    "ops@corp", ["finance@corp"],
                    f"Subject: overdue invoices\n\n{payload}",
                )
            cur2 = self.conn.cursor()
            cur2.execute("UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'")
            self.conn.commit()

        print(f"synced {len(rows)} invoices as {fmt}")
        return len(rows)
