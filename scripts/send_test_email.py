#!/usr/bin/env python3
"""
Send a test transaction email to your Gmail for testing the parser.
This spoofs the From address to match what the parsers expect.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

def send_test_chase_email(to_email: str):
    """Send a fake Chase transaction email."""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Your $42.50 transaction with your Chase card"
    msg['From'] = "noreply@chase.com"
    msg['To'] = to_email

    body = """
Hi,

A charge of $42.50 was approved for your transaction at Blue Bottle Coffee on 02/12/2026.

Card ending in 5678

Thanks,
Chase
"""

    msg.attach(MIMEText(body, 'plain'))

    # Note: This uses localhost SMTP - you may need to configure
    # Gmail SMTP settings or use a local mail server
    try:
        with smtplib.SMTP('localhost', 1025) as server:
            server.send_message(msg)
            print(f"✅ Test email sent to {to_email}")
            print("Subject:", msg['Subject'])
            print("From:", msg['From'])
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        print("\nNote: This requires a local SMTP server.")
        print("Alternative: Manually forward a real Chase/Venmo email to yourself")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_test_chase_email(sys.argv[1])
    else:
        print("Usage: python send_test_email.py your-email@gmail.com")