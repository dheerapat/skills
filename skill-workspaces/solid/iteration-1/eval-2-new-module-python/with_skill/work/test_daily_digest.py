"""Pins the digest seam. No deps: `python test_daily_digest.py` (pytest works too)."""

from datetime import date

from daily_digest import digest_for


class FakeCursor:
    def __init__(self):
        self.bound = None

    def execute(self, sql, params):
        self.bound = params

    def fetchone(self):
        return [7]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConn:
    def __init__(self):
        self.cur = FakeCursor()

    def cursor(self):
        return self.cur


def test_yesterday_and_half_open_bounds():
    conn = FakeConn()
    subject, body = digest_for(conn, today=date(2024, 3, 5))

    assert conn.cur.bound == (date(2024, 3, 4), date(2024, 3, 5))
    assert subject == "Signups 2024-03-04: 7"
    assert body == "7 new signups on 2024-03-04.\n"


if __name__ == "__main__":
    test_yesterday_and_half_open_bounds()
    print("ok")
