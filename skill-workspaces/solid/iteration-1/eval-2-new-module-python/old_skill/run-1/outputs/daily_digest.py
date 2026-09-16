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
