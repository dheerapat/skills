"""Report delivery. One reason to change: how the payload gets to finance."""
import smtplib

HOST = "mail.internal"
PORT = 587
ACCOUNT = "ops@corp"
PASSWORD = "apassword"
RECIPIENTS = ["finance@corp"]
SUBJECT = "overdue invoices"


class InvoiceMailer:
    """Sends a rendered payload over SMTP. smtplib is known only here."""

    def __init__(self, host=HOST, port=PORT, account=ACCOUNT, password=PASSWORD,
                 recipients=RECIPIENTS):
        self.host = host
        self.port = port
        self.account = account
        self.password = password
        self.recipients = recipients

    def send(self, payload):
        with smtplib.SMTP(self.host, self.port) as smtp:
            smtp.starttls()
            smtp.login(self.account, self.password)
            smtp.sendmail(
                self.account, self.recipients, f"Subject: {SUBJECT}\n\n{payload}"
            )
