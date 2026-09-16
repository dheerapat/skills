# Refactor: `invoice_sync.py` → SOLID

One file, same name, same public entry point. `InvoiceSyncManager(...).run(fmt="csv", dry_run=False)`
still connects to Postgres at construction, returns `len(rows)`, prints
`synced N invoices as <fmt>`, and raises `ValueError("unsupported format")`.

**Verified identical, not eyeballed:** the original class and the new one were run side by side
against the same fake connection/rows (incl. `Decimal`, `date`, `None`, and a vendor containing
`","` `"\n"` `"\t"`) for all 3 formats × `dry_run` on/off × 3 bad formats. Return value, stdout,
exception type+message, SQL text, commit count, mail payload and **order of side effects** all
matched — `RESULT: ALL IDENTICAL` (9/9 cases).

---

## What it looked like before

`InvoiceSyncManager` had **four** reasons to change: the SQL schema, the output formats
(an `if/elif/else` chain), the SMTP credentials/host, and stdout. Any new format meant editing
the one big method; nothing could be tested without a live DB and mail server.

## Structure after

| Layer | Abstraction (`Protocol`) | Implementation | Sole job |
|---|---|---|---|
| Storage | `InvoiceRepository` | `PostgresInvoiceRepository` | SQL: fetch overdue, mark synced |
| Format | `InvoiceReporter` | `CsvReporter` / `TsvReporter` / `JsonReporter` + `ReporterRegistry` | rows → payload string |
| Delivery | `InvoiceMailSender` | `SmtpInvoiceMailSender` | send payload over SMTP |
| Orchestration | — | `InvoiceSyncManager` | sequence the three, report the count |

`InvoiceSyncManager.run` is now 7 lines of pure sequencing:

```python
rows = self._repository.fetch_overdue()
payload = self._reporters.for_format(fmt).export(rows)   # raises ValueError here, as before
if not dry_run:
    self._mailer.send(payload)
    self._repository.mark_synced()
self._print(f"synced {len(rows)} invoices as {fmt}")
return len(rows)
```

---

## Rule by rule

**S — Single Responsibility.** Split the four reasons to change into four classes. SQL is now in
exactly one place (`PostgresInvoiceRepository`, with `SELECT_OVERDUE` / `UPDATE_SYNCED` as named
constants); format knowledge lives only in reporters; socket/credentials only in the mailer.

**O — Open/Closed.** The `if fmt == ... elif ...` chain is gone. Formats are self-describing
classes (`format = "csv"`) collected in `ReporterRegistry`, so `PdfReporter` is added by writing a
*new* class and passing it in (`registry.register(PdfReporter())` or
`InvoiceSyncManager(reporters=ReporterRegistry([...]))`) — no existing line of working code is
modified. Unknown formats are a `KeyError → ValueError` at one site instead of the tail of a
branch chain.

**L — Liskov Substitution.** Every `InvoiceReporter` implements `export(rows) -> str` for *any*
rows input with no raised-ness, no extra preconditions, and no narrower postcondition; none of
them needs constructor state, so all three are interchangeable in the registry. Nothing subclasses
a concrete class and then breaks its contract (contrast: a `Penguin.fly` shape). The check above
confirms all three satisfy the same observable contract, including the CSV `\r\n` terminator and
`default=str` on JSON.

**I — Interface Segregation.** No fat `Machine`-style interface. `InvoiceRepository`
exposes only `fetch_overdue` / `mark_synced`; `InvoiceMailSender` only `send`; `InvoiceReporter`
only `export`. The mailer never sees the repository, and the mailer's payload type is a plain
`str`, so a future webhook/S3 sender does not have to implement formatting or SQL to be used.

**D — Dependency Inversion.** `InvoiceSyncManager` depends on `Protocol`s, never on `psycopg2` or
`smtplib` directly. Concrete deps are constructor-injected with defaults preserving old behaviour:

```python
InvoiceSyncManager()                                   # -> prod, exactly as before
InvoiceSyncManager(repository=FakeRepo(), mailer=FakeMailer(), printer=rec.append)  # offline test
PostgresInvoiceRepository(dsn=dsn, connect=psycopg2.connect)   # connection factory injectable
```

`printer: Callable[[str], object] = print` replaces the hard-wired `print` — the last hidden
collaborator, and the one that made the old method untestable without capturing stdout.

---

## Deliberately *not* done (scope discipline)

- **No config/secret externalisation.** `DSN`, `mail.internal`, `ops@corp/apassword` are kept as
  literal defaults so behaviour is byte-identical. They are now *constructor parameters*, so
  reading them from env is a one-line change you can make when you're ready — but that is a
  behaviour change and you said behaviour must not change. Flag: those are live-looking prod
  credentials in a repo; rotating + moving them to a secret store is worth its own ticket.
- **No new entry point, no `main()`, no CLI, no retries, no logging framework, no package split.**
  Nothing asked for it; one file keeps imports (`from invoice_sync import InvoiceSyncManager`)
  working untouched.
- **No rows→dataclass conversion.** Rows stay raw tuples because `csv.writer.writerow(row)`,
  `str(c)` and `dict(zip(COLUMNS, row))` are exactly what produced the old bytes.
- **No test file added** to the repo (you said don't touch anything else). The equivalence harness
  I used lives in `/tmp/eq/check.py` — say the word and I'll drop it in as `test_invoice_sync.py`.

## One caveat worth knowing

Behaviour is identical, including two pre-existing quirks I did *not* "fix" because fixing them
changes behaviour: (1) `mark_synced()` updates **all** `OPEN` invoices, not just the >30-day ones
that were exported; (2) on a format error the SELECT has already run and the connection stays
open (no `close()` existed before either). Both are one-line changes if you want them —
`UPDATE ... WHERE id = ANY(%s)` and a `close()`/context manager respectively.
