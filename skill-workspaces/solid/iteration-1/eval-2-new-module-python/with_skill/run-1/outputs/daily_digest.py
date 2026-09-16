"""Daily signup digest: mail ops@corp the number of signups from yesterday.

Run once a day from cron, after midnight so "yesterday" is complete:

    15 6 * * * cd /srv/corp && /usr/bin/env python3 /srv/corp/daily_digest.py

No try/except around the work on purpose: a traceback on stderr makes cron mail
the failure to MAILTO. A digest that silently doesn't arrive is worse than one
that visibly fails.
"""

from __future__ import annotations

import os
from contextlib import closing
from datetime import date, timedelta

import notify

RECIPIENT = "ops@corp"

# Half-open range so the count can use an index on signups.created_at; Postgres
# widens the `date` bounds to midnight in the session timezone. If signups are
# stored in UTC and ops reads the number in local time, cast here:
#   WHERE created_at >= %s::timestamptz AT TIME ZONE 'UTC'
COUNT_SQL = """
    SELECT count(*)
    FROM signups
    WHERE created_at >= %s AND created_at < %s
"""


def count_signups(cur, day: date) -> int:
    """Signups created on `day`. `cur` is any DB-API cursor (real or fake)."""
    cur.execute(COUNT_SQL, (day, day + timedelta(days=1)))
    return cur.fetchone()[0]


def render(day: date, count: int) -> tuple[str, str]:
    """(subject, body) — the only thing that changes when ops restates the ask."""
    return (
        f"Signups {day.isoformat()}: {count}",
        f"{count} new signups on {day.isoformat()}.\n",
    )


def digest_for(conn, today: date) -> tuple[str, str]:
    """Build the digest for the day before `today`, reading from `conn`.

    Clock and connection come in as arguments, so this runs in a test with no
    Postgres and no SMTP.
    """
    yesterday = today - timedelta(days=1)
    with conn.cursor() as cur:
        return render(yesterday, count_signups(cur, yesterday))


def main() -> None:
    """Wiring only: driver, DSN, clock, mail. Everything above is pure."""
    import psycopg2  # imported here so the logic stays importable without the driver

    with closing(psycopg2.connect(os.environ["PG_DSN"])) as conn:
        subject, body = digest_for(conn, date.today())
    notify.send(RECIPIENT, subject, body)


if __name__ == "__main__":
    main()
