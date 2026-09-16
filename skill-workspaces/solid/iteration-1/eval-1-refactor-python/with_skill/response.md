# invoice_sync.py — refactored

`cd work && python3 -m unittest test_invoice_sync -v` → 4 tests, OK. That run compares 14 scenarios against behavior I pinned from the **original** code before touching it.

## Diagnosis (what the gate actually matched)

- **S** — `InvoiceSyncManager` had four reasons to change living in one class: the SQL, the report format, email delivery, and the job's ordering. The docstring admitted it ("One file, one class, everything in it").
- **O** — `if fmt == "csv" / elif "tsv" / elif "json" / else raise` — a string-keyed chain; every new format meant editing code that already worked.
- **D** — `psycopg2.connect(DSN)` in `__init__` and `smtplib.SMTP(...)` mid-method. Nothing was testable without a live billing DB and the internal mail server (proof: this checkout can't even `import psycopg2`).
- **L / I** — no matches. No subtypes, no interfaces. Nothing done for them.

## The seams

| File | One reason to change |
| --- | --- |
| `invoice_repository.py` | the database — `overdue()`, `mark_synced()`, and the lazy `connect()` (only file that knows psycopg2) |
| `invoice_formatting.py` | the report's shape — `FORMATTERS` dict + `render()` |
| `invoice_mail.py` | delivery — only file that knows `smtplib`, host, creds |
| `invoice_sync.py` | what the job does and in what order — pure `sync_invoices()` + edge `run_invoice_sync()` |
| `test_invoice_sync.py` | characterization baseline (stdlib `unittest`, no new deps) |

Key moves:

- **OCP:** the chain became data. Add a format = write one `(rows) -> str` function + one `FORMATTERS` entry. `_csv` and `_tsv` are *not* collapsed into a parameterized delimiter (as tempting as it looks): `csv.writer` quotes fields, uses `\r\n`, and renders `NULL` as empty rather than `"None"` — merging them would have changed output. A test pins both.
- **DIP:** `sync_invoices(repo, notify, fmt, dry_run)` receives its collaborators. `notify` is `Callable[[str], None]` — the seam is a function parameter, so a test passes `sent.append`. Concrete connection and mailer are built once, at the edge, in `run_invoice_sync`.
- **DRY without coupling:** `COLUMNS` is the single source of truth; the repository builds the `SELECT` from it, so query columns and report headers can't drift. Asserted byte-identical against the original SQL.

## Deliberately not done

- **No `Protocol`/ABC/factory.** `Notifier` and the repository each have one implementation plus a duck-typed test double; an interface would be a pass-through. `InvoiceSyncManager` is gone (nothing else in the repo referenced it — grep is clean); call `run_invoice_sync(fmt, dry_run)` or import `sync_invoices`.
- **Bug left alone, not mine to fix:** `UPDATE invoices SET status='SYNCED' WHERE status='OPEN'` marks *every* open invoice synced, not just the >30-day ones the report contains. Also: mail creds and DSN are still hardcoded constants, and `print(f"synced {len(rows)} invoices")` says "1 invoices". Preserved verbatim. Say the word and I'll fix any of the three — the UPDATE one first.

```text
S: InvoiceSyncManager was edited for SQL, format, email, and job order — four jobs.
Seam: split into repository/formatting/mail + orchestration; formats became a dict; psycopg2/smtplib constructed only at the edge.
Not done: no Protocol for Notifier or the repository (single implementation — callable is the seam); UPDATE marks all OPEN rows.
```
