"""Characterization tests: the refactor must reproduce invoice_sync.py's recorded
behavior exactly — payloads, SQL, SMTP conversation, stdout, return values, and the
exception raised for an unknown format.

EXPECTED was captured from the original single-class implementation (14 scenarios).

Run: python3 -m unittest test_invoice_sync -v
"""
import contextlib
import io
import json
import unittest
from datetime import datetime
from decimal import Decimal

import invoice_formatting
import invoice_mail
from invoice_formatting import COLUMNS, render
from invoice_mail import InvoiceMailer
from invoice_repository import InvoiceRepository
from invoice_sync import sync_invoices

# --- baseline: behavior recorded from the original code. Do not edit. ------
EXPECTED = [{'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall'],
               ['execute',
                "UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'"],
               ['commit']],
  'error': None,
  'return': 3,
  'smtp_log': [['smtp_connect', 'mail.internal', 587],
               ['starttls'],
               ['login', 'ops@corp', 'apassword'],
               ['sendmail',
                'ops@corp',
                ['finance@corp'],
                'Subject: overdue invoices\n'
                '\n'
                'id,vendor,amount,currency,issued_at\r\n'
                '1,"Acme, Inc.",1250.00,USD,2025-01-05 00:00:00\r\n'
                '2,"Say ""hi""",,EUR,2025-02-01 13:30:00\r\n'
                '3,Tab\tVendor,0.10,USD,2025-03-09 23:59:59\r\n'],
               ['smtp_close']],
  'stdout': 'synced 3 invoices as csv\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall']],
  'error': None,
  'return': 3,
  'smtp_log': [],
  'stdout': 'synced 3 invoices as csv\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall'],
               ['execute',
                "UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'"],
               ['commit']],
  'error': None,
  'return': 3,
  'smtp_log': [['smtp_connect', 'mail.internal', 587],
               ['starttls'],
               ['login', 'ops@corp', 'apassword'],
               ['sendmail',
                'ops@corp',
                ['finance@corp'],
                'Subject: overdue invoices\n'
                '\n'
                '1\tAcme, Inc.\t1250.00\tUSD\t2025-01-05 00:00:00\n'
                '2\tSay "hi"\tNone\tEUR\t2025-02-01 13:30:00\n'
                '3\tTab\tVendor\t0.10\tUSD\t2025-03-09 23:59:59'],
               ['smtp_close']],
  'stdout': 'synced 3 invoices as tsv\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall']],
  'error': None,
  'return': 3,
  'smtp_log': [],
  'stdout': 'synced 3 invoices as tsv\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall'],
               ['execute',
                "UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'"],
               ['commit']],
  'error': None,
  'return': 3,
  'smtp_log': [['smtp_connect', 'mail.internal', 587],
               ['starttls'],
               ['login', 'ops@corp', 'apassword'],
               ['sendmail',
                'ops@corp',
                ['finance@corp'],
                'Subject: overdue invoices\n'
                '\n'
                '[{"id": 1, "vendor": "Acme, Inc.", "amount": "1250.00", "currency": '
                '"USD", "issued_at": "2025-01-05 00:00:00"}, {"id": 2, "vendor": "Say '
                '\\"hi\\"", "amount": null, "currency": "EUR", "issued_at": '
                '"2025-02-01 13:30:00"}, {"id": 3, "vendor": "Tab\\tVendor", "amount": '
                '"0.10", "currency": "USD", "issued_at": "2025-03-09 23:59:59"}]'],
               ['smtp_close']],
  'stdout': 'synced 3 invoices as json\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall']],
  'error': None,
  'return': 3,
  'smtp_log': [],
  'stdout': 'synced 3 invoices as json\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall'],
               ['execute',
                "UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'"],
               ['commit']],
  'error': None,
  'return': 0,
  'smtp_log': [['smtp_connect', 'mail.internal', 587],
               ['starttls'],
               ['login', 'ops@corp', 'apassword'],
               ['sendmail',
                'ops@corp',
                ['finance@corp'],
                'Subject: overdue invoices\n\nid,vendor,amount,currency,issued_at\r\n'],
               ['smtp_close']],
  'stdout': 'synced 0 invoices as csv\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall'],
               ['execute',
                "UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'"],
               ['commit']],
  'error': None,
  'return': 0,
  'smtp_log': [['smtp_connect', 'mail.internal', 587],
               ['starttls'],
               ['login', 'ops@corp', 'apassword'],
               ['sendmail',
                'ops@corp',
                ['finance@corp'],
                'Subject: overdue invoices\n\n'],
               ['smtp_close']],
  'stdout': 'synced 0 invoices as tsv\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall'],
               ['execute',
                "UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'"],
               ['commit']],
  'error': None,
  'return': 0,
  'smtp_log': [['smtp_connect', 'mail.internal', 587],
               ['starttls'],
               ['login', 'ops@corp', 'apassword'],
               ['sendmail',
                'ops@corp',
                ['finance@corp'],
                'Subject: overdue invoices\n\n[]'],
               ['smtp_close']],
  'stdout': 'synced 0 invoices as json\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall']],
  'error': None,
  'return': 1,
  'smtp_log': [],
  'stdout': 'synced 1 invoices as csv\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall']],
  'error': None,
  'return': 1,
  'smtp_log': [],
  'stdout': 'synced 1 invoices as json\n'},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall']],
  'error': 'ValueError: unsupported format',
  'return': None,
  'smtp_log': [],
  'stdout': ''},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall']],
  'error': 'ValueError: unsupported format',
  'return': None,
  'smtp_log': [],
  'stdout': ''},
 {'conn_log': [['execute',
                'SELECT id, vendor, amount, currency, issued_at FROM invoices WHERE '
                "status = 'OPEN' AND issued_at < now() - interval '30 days'"],
               ['fetchall'],
               ['execute',
                "UPDATE invoices SET status = 'SYNCED' WHERE status = 'OPEN'"],
               ['commit']],
  'error': None,
  'return': 3,
  'smtp_log': [['smtp_connect', 'mail.internal', 587],
               ['starttls'],
               ['login', 'ops@corp', 'apassword'],
               ['sendmail',
                'ops@corp',
                ['finance@corp'],
                'Subject: overdue invoices\n'
                '\n'
                'id,vendor,amount,currency,issued_at\r\n'
                '1,"Acme, Inc.",1250.00,USD,2025-01-05 00:00:00\r\n'
                '2,"Say ""hi""",,EUR,2025-02-01 13:30:00\r\n'
                '3,Tab\tVendor,0.10,USD,2025-03-09 23:59:59\r\n'],
               ['smtp_close']],
  'stdout': 'synced 3 invoices as csv\n'}]
# ---------------------------------------------------------------------------

ROWS = {
    "three": [
        (1, "Acme, Inc.", Decimal("1250.00"), "USD", datetime(2025, 1, 5, 0, 0)),
        (2, 'Say "hi"', None, "EUR", datetime(2025, 2, 1, 13, 30)),
        (3, "Tab\tVendor", Decimal("0.10"), "USD", datetime(2025, 3, 9, 23, 59, 59)),
    ],
    "empty": [],
    "one": [(42, "Solo", Decimal("7.00"), "GBP", datetime(2025, 4, 1))],
}

# (rows, fmt, dry_run). fmt=None => call with the defaults, like the original did.
CASES = [
    ("three", "csv", False), ("three", "csv", True),
    ("three", "tsv", False), ("three", "tsv", True),
    ("three", "json", False), ("three", "json", True),
    ("empty", "csv", False), ("empty", "tsv", False), ("empty", "json", False),
    ("one", "csv", True), ("one", "json", True),
    ("three", "xlsx", True), ("three", "xlsx", False),
    ("three", None, None),
]

SELECT = ("SELECT id, vendor, amount, currency, issued_at FROM invoices "
          "WHERE status = 'OPEN' AND issued_at < now() - interval '30 days'")


class FakeCursor:
    def __init__(self, log, rows):
        self.log, self.rows = log, rows

    def execute(self, sql, *a, **kw):
        self.log.append(["execute", " ".join(sql.split())])

    def fetchall(self):
        self.log.append(["fetchall"])
        return self.rows


class FakeConn:
    """Test double for a psycopg2 connection: a plain object, no mock library."""

    def __init__(self, rows):
        self.rows, self.log = rows, []

    def cursor(self):
        return FakeCursor(self.log, self.rows)

    def commit(self):
        self.log.append(["commit"])


class RecordingSMTP:
    """Stands in for smtplib.SMTP inside invoice_mail."""

    def __init__(self, host, port, log):
        self.log = log
        self.log.append(["smtp_connect", host, port])

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.log.append(["smtp_close"])
        return False

    def starttls(self):
        self.log.append(["starttls"])

    def login(self, user, pw):
        self.log.append(["login", user, pw])

    def sendmail(self, frm, to, msg):
        self.log.append(["sendmail", frm, tuple(to), msg])


def run(rows_key, fmt, dry_run):
    conn = FakeConn(ROWS[rows_key])
    smtp_log = []
    real = invoice_mail.smtplib.SMTP
    invoice_mail.smtplib.SMTP = lambda host, port: RecordingSMTP(host, port, smtp_log)
    out = io.StringIO()
    try:
        args = () if fmt is None else (fmt, dry_run)
        with contextlib.redirect_stdout(out):
            try:
                ret = sync_invoices(InvoiceRepository(conn), InvoiceMailer().send, *args)
            except Exception as exc:
                ret, err = None, f"{type(exc).__name__}: {exc}"
            else:
                err = None
    finally:
        invoice_mail.smtplib.SMTP = real
    return {
        "conn_log": conn.log,
        "error": err,
        "return": ret,
        "smtp_log": smtp_log,
        "stdout": out.getvalue(),
    }


class CharacterizationTest(unittest.TestCase):
    def test_all_scenarios_match_baseline(self):
        self.assertEqual(len(CASES), len(EXPECTED))
        for (key, fmt, dry), want in zip(CASES, EXPECTED):
            with self.subTest(rows=key, fmt=fmt, dry_run=dry):
                got = run(key, fmt, dry)
                self.assertEqual(json.loads(json.dumps(got, default=str)),
                                 json.loads(json.dumps(want, default=str)))

    def test_sql_is_unchanged(self):
        conn = FakeConn(ROWS["empty"])
        with contextlib.redirect_stdout(io.StringIO()):
            sync_invoices(InvoiceRepository(conn), lambda payload: None, "csv", True)
        self.assertEqual(conn.log[0], ["execute", SELECT])
        self.assertEqual(COLUMNS, ["id", "vendor", "amount", "currency", "issued_at"])

    def test_new_format_added_alongside_not_inside(self):
        """OCP: registering a format never re-runs or edits an existing renderer."""
        def xml(rows):
            return "<rows/>"

        before = {f: render(ROWS["three"], f) for f in invoice_formatting.FORMATTERS}
        invoice_formatting.FORMATTERS["xml"] = xml
        try:
            self.assertEqual(render(ROWS["three"], "xml"), "<rows/>")
            self.assertEqual({f: render(ROWS["three"], f) for f in before}, before)
        finally:
            del invoice_formatting.FORMATTERS["xml"]

    def test_unknown_format_raises_before_any_side_effect(self):
        conn = FakeConn(ROWS["three"])
        sent = []
        with self.assertRaises(ValueError) as ctx:
            sync_invoices(InvoiceRepository(conn), sent.append, "xlsx", False)
        self.assertEqual(str(ctx.exception), "unsupported format")
        self.assertEqual(sent, [])
        self.assertEqual([x[1] for x in conn.log if x[0] == "execute"], [SELECT])


if __name__ == "__main__":
    unittest.main()
