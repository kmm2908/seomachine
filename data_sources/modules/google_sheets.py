"""
Google Sheets Integration

Reads location data from a Google Sheet and writes status updates back.
Used by the /geo-batch command to manage the geo content writing queue.

Sheet format:
  Column A: Location address including postcode (e.g. "Byres Road Glasgow G12")
  Column B: Status dropdown — "Write Now" | "pause" | "DONE" | "Images o/s"
  Column C: Cost (written by script after generation, e.g. "$0.43")
  Column D: Business abbreviation dropdown (e.g. "GTM") — matches a file in clients/
  Column E: Content type (e.g. "geo", "service", "location", "topical", "blog") — defaults to "blog" if empty
  Column F: File path (auto-set when status = "Images o/s"; cleared on DONE)

Usage:
  python3 google_sheets.py read
  python3 google_sheets.py read --range A2:D10
  python3 google_sheets.py update --row 3 --status DONE
  python3 google_sheets.py email --subject "..." --body "..."
"""

import argparse
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load from project root .env (two levels up from data_sources/modules/)
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_root, '.env'))

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
DEFAULT_RANGE = 'A2:F1000'
STATUS_COLUMN = 'B'
QUEUE_VALUE = 'Write Now'
DONE_VALUE = 'DONE'
IMAGES_PENDING_VALUE = 'Images o/s'
REVIEW_REQUIRED_VALUE = 'Review Required'


def get_service():
    credentials_path = os.getenv('GA4_CREDENTIALS_PATH') or os.path.join(
        os.path.dirname(__file__), '../../credentials/ga4-credentials.json'
    )
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=credentials)


def get_sheet_id() -> str:
    sheet_id = os.getenv('GEO_LOCATIONS_SHEET_ID')
    if not sheet_id:
        raise ValueError("GEO_LOCATIONS_SHEET_ID not set in .env")
    return sheet_id


def read_pending(range_str: Optional[str] = None) -> list[dict]:
    """Return rows where Column B = 'right now'."""
    service = get_service()
    sheet_id = get_sheet_id()
    target_range = range_str or DEFAULT_RANGE

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=target_range)
        .execute()
    )

    rows = result.get('values', [])

    # Determine start row from range (e.g. A2:B10 → row 2)
    start_row = 2
    if target_range and ':' in target_range:
        start_part = target_range.split(':')[0]
        digits = ''.join(c for c in start_part if c.isdigit())
        if digits:
            start_row = int(digits)

    pending = []
    for i, row in enumerate(rows):
        address = row[0].strip() if len(row) > 0 else ''
        status = row[1].strip() if len(row) > 1 else ''
        business = row[3].strip() if len(row) > 3 else ''
        content_type = row[4].strip() if len(row) > 4 else ''
        file_path = row[5].strip() if len(row) > 5 else ''

        if not address:
            continue

        if status.lower() not in (QUEUE_VALUE.lower(), IMAGES_PENDING_VALUE.lower()):
            continue

        pending.append({
            'row': start_row + i,
            'address': address,
            'business': business,
            'content_type': content_type or 'blog',
            'status': status,
            'file_path': file_path,
        })

    return pending


def update_status(row_number: int, status: str) -> None:
    """Write status value to Column B of the given row."""
    service = get_service()
    sheet_id = get_sheet_id()
    cell_range = f'{STATUS_COLUMN}{row_number}'

    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=cell_range,
        valueInputOption='RAW',
        body={'values': [[status]]},
    ).execute()


def update_file_path(row_number: int, path_str: str) -> None:
    """Write file path to Column F of the given row. Pass empty string to clear."""
    service = get_service()
    sheet_id = get_sheet_id()
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f'F{row_number}',
        valueInputOption='RAW',
        body={'values': [[path_str]]},
    ).execute()


def update_cost(row_number: int, cost_str: str) -> None:
    """Write cost value to Column C of the given row."""
    service = get_service()
    sheet_id = get_sheet_id()
    cell_range = f'C{row_number}'

    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=cell_range,
        valueInputOption='RAW',
        body={'values': [[cost_str]]},
    ).execute()


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


def main():
    parser = argparse.ArgumentParser(description='Google Sheets geo locations manager')
    subparsers = parser.add_subparsers(dest='command', required=True)

    read_parser = subparsers.add_parser('read', help='Read queued locations (status = "right now")')
    read_parser.add_argument('--range', help='Sheet range e.g. A2:B10', default=None)

    update_parser = subparsers.add_parser('update', help='Update row status')
    update_parser.add_argument('--row', type=int, required=True, help='Row number')
    update_parser.add_argument('--status', required=True, help='Status value to write')

    email_parser = subparsers.add_parser('email', help='Send summary email')
    email_parser.add_argument('--subject', required=True, help='Email subject')
    email_parser.add_argument('--body', required=True, help='Email body text')

    args = parser.parse_args()

    if args.command == 'read':
        pending = read_pending(args.range)
        print(json.dumps(pending, indent=2))

    elif args.command == 'update':
        update_status(args.row, args.status)
        print(json.dumps({'row': args.row, 'status': args.status}))

    elif args.command == 'email':
        send_email(args.subject, args.body)
        print(json.dumps({'sent': True, 'subject': args.subject}))


if __name__ == '__main__':
    main()
