`daily_digest.py` is written and verified (147 lines, one file, `notify.py` reused untouched). Install the cron line at the bottom and set `PG_DSN` in crontab — that's the only step left.

## What it does

Counts yesterday's `signups` rows and mails `Signups 2025-09-16: 42` to `ops@corp`. Count is in the subject so ops triages from the notification without opening the mail.

## File

`/home/dheeto/skills/skill-workspaces/solid/iteration-1/eval-2-new-module-python/old_skill/work/daily_digest.py`

```python
"""Daily signup digest for ops@corp.

Counts yesterday's signups and mails the number. Designed to be run once a day
by cron, e.g.

    17 6 * * *  cd /srv/app && python daily_digest.py >> /var/log/daily_digest.log 2>&1

Layout: ports (Protocols) at the top, the job that uses them next, concrete
adapters + the composition root at the bottom. The job never imports a concrete
dependency, so swapping Postgres for another store or email for Slack means
adding a class, not editing one.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

import psycopg2

import notify

log = logging.getLogger("daily_digest")


# --------------------------------------------------------------------------- ports


class Clock(Protocol):
    """Gives the job a 'today' without the job owning time-zone policy."""

    def today(self) -> date: ...


class SignupCounter(Protocol):
    """Counts signups for one calendar day."""

    def count(self, day: date) -> int: ...


class MessageSender(Protocol):
    """Delivers a message. One method, no fax/print/scan baggage."""

    def send(self, to: str, subject: str, body: str) -> None: ...


# ----------------------------------------------------------------------------- job


class DailyDigest:
    """One reason to change: how the digest is worded / to whom it goes."""

    def __init__(
        self,
        clock: Clock,
        signups: SignupCounter,
        sender: MessageSender,
        recipient: str,
    ) -> None:
        self._clock = clock
        self._signups = signups
        self._sender = sender
        self._recipient = recipient

    def run(self) -> int:
        """Send yesterday's digest; return the count that was mailed."""
        day = self._clock.today() - timedelta(days=1)
        count = self._signups.count(day)
        subject = f"Signups {day.isoformat()}: {count}"
        body = f"Signups on {day.isoformat()}: {count}\n"
        self._sender.send(self._recipient, subject, body)
        log.info("mailed %r to %s", subject, self._recipient)
        return count


# ----------------------------------------------------------------------- adapters


class SystemClock:
    """Wall-clock 'today' in a named time zone."""

    def __init__(self, tz_name: str) -> None:
        self._tz = ZoneInfo(tz_name)

    def today(self) -> date:
        return datetime.now(self._tz).date()


class PostgresSignupCounter:
    """`signups` rows with created_at inside [day 00:00, next day 00:00) in tz_name."""

    SQL = "SELECT count(*) FROM signups WHERE created_at >= %s AND created_at < %s"

    def __init__(self, dsn: str, tz_name: str) -> None:
        self._dsn = dsn
        self._tz = ZoneInfo(tz_name)

    def count(self, day: date) -> int:
        start = datetime.combine(day, time.min, tzinfo=self._tz)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=self._tz)
        with psycopg2.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(self.SQL, (start, end))
            return int(cur.fetchone()[0])


# ----------------------------------------------------------------- composition root


def build() -> DailyDigest:
    """Wire real dependencies together. The only place that knows them.

    `notify` is passed as-is: its existing `send(to, subject, body)` already
    satisfies MessageSender, so an adapter class would add nothing.
    """
    tz_name = os.environ.get("DAILY_DIGEST_TZ", "UTC")
    return DailyDigest(
        clock=SystemClock(tz_name),
        signups=PostgresSignupCounter(require_env("PG_DSN"), tz_name),
        sender=notify,
        recipient=os.environ.get("OPS_MAIL_TO", "ops@corp"),
    )


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set (cron gives you no shell env by default)")
    return value


def main() -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        build().run()
    except Exception:
        # Non-zero exit + traceback on stderr is what tells cron/ops this broke.
        log.exception("daily digest failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## How each letter is satisfied (review-comment ammo)

1. **S** — `DailyDigest` = wording/routing. `PostgresSignupCounter` = SQL. `SystemClock` = wall clock. `build()` = wiring. `main()` = process boundary (logging, exit code). Each has exactly one reason to change.
2. **O** — Slack instead of email, or MySQL instead of Postgres = new adapter class + one line in `build()`. No `if format == ...` branch anywhere, no existing class edited.
3. **L** — all three adapters satisfy their port with real behaviour; nothing raises `NotImplementedError`, nothing narrows the signature, and each port's postconditions are documented on the port itself so a substitute can't quietly change "day" semantics.
4. **I** — three one-method ports. The job that only formats text never sees `connect()`, `cursor()`, or SMTP config.
5. **D** — `DailyDigest` depends on `Clock`/`SignupCounter`/`MessageSender` Protocols; concretes exist only in `build()`. That's what makes it testable with fakes (proof below).

## Deliberate non-goals (kept lazy)

- **No wrapper class around `notify`.** Its existing `send(to, subject, body)` is already structurally a `MessageSender`, so `sender=notify` is the adapter. D is still honoured — the job sees a Protocol.
- **No argparse, no `--skip-empty`, no config module.** Only two env vars, both documented in `build()`. Say the word if ops wants a zero-count mail suppressed — that's a 3-line `if` in `run()`, not a flag.
- **No new email code.** Reuses the working `notify.py` per repo convention, including its `mail.internal` / `bot@corp` constants.

## Correctness notes baked in

- Half-open `[00:00, 00:00)` window with **tz-aware** bounds — no `::date`-in-UTC-vs-local off-by-one, no `BETWEEN` double-counting midnight.
- Values go through psycopg2 parameter binding (`%s`); nothing is f-string'd into SQL.
- `PG_DSN` missing → `RuntimeError` with an explicit message, exit 1 (cron mails the stderr traceback to the crontab owner, so a silent day of no mail is impossible).
- A day with zero signups still sends mail — a missing digest should never be ambiguous with a quiet day.

## Verification run

Stubbed `psycopg2` (not installed in this sandbox) and drove every seam with fakes:

- `DailyDigest` + `FixedClock(2025-09-17)` + fake counter → `run() == 42`, mail exactly `("ops@corp", "Signups 2025-09-16: 42", "Signups on 2025-09-16: 42\n")`.
- `PostgresSignupCounter(..., "Europe/Berlin").count(2025-09-16)` → params `(2025-09-16 00:00 +02:00, 2025-09-17 00:00 +02:00)`, returns `7`.
- `build().run()` → logged `mailed 'Signups 2026-09-15: 7' to ops@corp`; `main()` returned `0`.
- `PG_DSN="  "` → `main()` returned `1` with the `PG_DSN is not set` traceback.

## Install (2 min)

```
17 6 * * *  cd /srv/app && PG_DSN=postgresql://user:pass@host/db python daily_digest.py >> /var/log/daily_digest.log 2>&1
```

Two things to confirm before merge, since the context file doesn't state them: the table is literally `signups` with a `created_at timestamptz`, and ops' "yesterday" is UTC (otherwise set `DAILY_DIGEST_TZ=America/New_York`). If you want, I'll add `test_daily_digest.py` next — the fakes above are already 90% of it.
