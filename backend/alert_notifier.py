import json
import os
import smtplib
from pathlib import Path
from datetime import datetime
from email.message import EmailMessage

CONTACTS_FILE = Path("alert_contacts.json")
LOG_FILE = Path("alert_notifications.log")

def load_contacts():
    if CONTACTS_FILE.exists():
        return json.loads(CONTACTS_FILE.read_text())
    return []

def send_email(to_email, subject, body):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not all([smtp_host, smtp_user, smtp_pass]):
        raise RuntimeError("SMTP settings missing")

    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

def send_test_alert(message):
    contacts = [c for c in load_contacts() if c.get("enabled")]
    results = []

    for c in contacts:
        status = "EMAIL_SENT"
        error = None

        try:
            if c.get("email"):
                send_email(
                    c["email"],
                    "GodsEye Maritime Intelligence Test Alert",
                    message
                )
        except Exception as e:
            status = "EMAIL_FAILED"
            error = str(e)

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "to": c,
            "message": message,
            "mode": status,
            "error": error
        }
        results.append(entry)

    with LOG_FILE.open("a") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    return results
