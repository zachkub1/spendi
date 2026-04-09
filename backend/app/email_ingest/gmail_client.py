"""
Gmail API client wrapper.
Provides simplified interface for Gmail API operations.
"""
from typing import Optional
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
import logging

logger = logging.getLogger(__name__)


class GmailClient:
    """Wrapper for Gmail API operations."""

    def __init__(self, credentials: Credentials):
        """
        Initialize Gmail client with OAuth credentials.

        Args:
            credentials: Google OAuth2 credentials
        """
        self.service = build('gmail', 'v1', credentials=credentials)

    def list_messages(
        self,
        sender_filter: Optional[list[str]] = None,
        after_date: Optional[str] = None,
        max_results: int = 100
    ) -> list[dict]:
        """
        List messages matching filters.

        Args:
            sender_filter: List of sender domains to filter by (e.g., ["chase.com", "venmo.com"])
            after_date: Date filter in format "YYYY/MM/DD"
            max_results: Maximum number of messages to return

        Returns:
            List of message metadata dicts with 'id' and 'threadId'
        """
        query_parts = []

        # Build sender filter query
        if sender_filter:
            sender_queries = [f"from:@{domain}" for domain in sender_filter]
            query_parts.append(f"({' OR '.join(sender_queries)})")

        # Add date filter
        if after_date:
            query_parts.append(f"after:{after_date}")

        query = " ".join(query_parts) if query_parts else None

        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages matching filters")
            return messages

        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            raise

    def get_message(self, message_id: str) -> dict:
        """
        Get full message by ID.

        Args:
            message_id: Gmail message ID

        Returns:
            Dict with keys: id, subject, from, date, body, internalDate
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = {h['name']: h['value'] for h in message['payload']['headers']}

            # Extract body (handle multipart messages)
            body = self._extract_body(message['payload'])

            return {
                'id': message['id'],
                'subject': headers.get('Subject', ''),
                'from': headers.get('From', ''),
                'date': headers.get('Date', ''),
                'internalDate': message.get('internalDate'),  # Gmail's reliable timestamp (milliseconds since epoch)
                'body': body
            }

        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise

    def _extract_body(self, payload: dict) -> str:
        """
        Extract message body from payload.
        Recursively handles nested multipart (e.g. multipart/mixed → multipart/alternative → text/plain).
        Preference order: text/plain > nested multipart > text/html (converted to plain text).
        """
        mime_type = payload.get('mimeType', '')

        # Single part with inline data
        if 'data' in payload.get('body', {}):
            raw = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            return self._html_to_text(raw) if mime_type == 'text/html' else raw

        parts = payload.get('parts', [])

        # Pass 1: prefer text/plain at this level
        for part in parts:
            if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

        # Pass 2: recurse into nested multipart containers
        for part in parts:
            if part.get('mimeType', '').startswith('multipart/'):
                result = self._extract_body(part)
                if result:
                    return result

        # Pass 3: fallback to HTML converted to plain text
        for part in parts:
            if part.get('mimeType') == 'text/html' and 'data' in part.get('body', {}):
                raw = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                return self._html_to_text(raw)

        return ""

    @staticmethod
    def _html_to_text(html: str) -> str:
        """
        Convert HTML email body to plain text suitable for regex parsing.
        Preserves table cell boundaries as whitespace so field:value patterns still match.
        """
        import re
        import html as html_lib

        # Drop style/script blocks
        html = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Table rows → newline, cells → tab (keeps "Field\tValue" alignment)
        html = re.sub(r'</tr\s*>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<td[^>]*>', '\t', html, flags=re.IGNORECASE)
        # Block elements → newline
        html = re.sub(r'<(?:br|p|div|h[1-6])\b[^>]*/?>',  '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</(?:p|div|h[1-6])>', '\n', html, flags=re.IGNORECASE)
        # Strip remaining tags
        html = re.sub(r'<[^>]+>', '', html)
        # Decode entities (&amp; etc.)
        html = html_lib.unescape(html)
        # Collapse inline whitespace; leave newlines intact
        html = re.sub(r'[ \t]+', ' ', html)
        # Clean up lines
        lines = [ln.strip() for ln in html.splitlines()]
        return '\n'.join(ln for ln in lines if ln)
