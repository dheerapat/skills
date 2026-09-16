# Project notes

`notify.py` already exists and works:

```python
import smtplib

SMTP_HOST = "mail.internal"
MAIL_FROM = "bot@corp"

def send(to: str, subject: str, body: str) -> None:
    with smtplib.SMTP(SMTP_HOST, 587) as s:
        s.starttls()
        s.sendmail(MAIL_FROM, [to], f"Subject: {subject}\n\n{body}")
```

Our DB access in this repo is always `psycopg2.connect(os.environ["PG_DSN"])`.
Ops wants a daily digest of yesterday's signup count mailed to ops@corp.
