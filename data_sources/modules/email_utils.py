"""SMTP email utility for batch summary notifications."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(subject: str, body: str) -> None:
    """Send a summary email via SMTP to all addresses in GEO_EMAIL_TO."""
    smtp_host = os.getenv('GEO_EMAIL_SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('GEO_EMAIL_SMTP_PORT', '587'))
    smtp_user = os.getenv('GEO_EMAIL_SMTP_USER', '')
    smtp_pass = os.getenv('GEO_EMAIL_SMTP_PASS', '')
    from_addr = os.getenv('GEO_EMAIL_FROM', smtp_user)
    to_raw = os.getenv('GEO_EMAIL_TO', '')

    if not smtp_user or not smtp_pass:
        raise ValueError("GEO_EMAIL_SMTP_USER and GEO_EMAIL_SMTP_PASS must be set in .env")
    if not to_raw:
        raise ValueError("GEO_EMAIL_TO must be set in .env")

    recipients = [addr.strip() for addr in to_raw.split(',') if addr.strip()]

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, recipients, msg.as_string())
