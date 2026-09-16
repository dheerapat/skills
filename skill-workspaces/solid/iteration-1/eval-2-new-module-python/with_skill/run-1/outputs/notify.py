import smtplib

SMTP_HOST = "mail.internal"
MAIL_FROM = "bot@corp"


def send(to: str, subject: str, body: str) -> None:
    with smtplib.SMTP(SMTP_HOST, 587) as s:
        s.starttls()
        s.sendmail(MAIL_FROM, [to], f"Subject: {subject}\n\n{body}")
