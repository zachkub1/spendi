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
            Dict with keys: id, subject, from, date, body
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
                'body': body
            }

        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise

    def _extract_body(self, payload: dict) -> str:
        """
        Extract message body from payload.
        Handles plain text and multipart messages.
        """
        if 'body' in payload and 'data' in payload['body']:
            # Single part message
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        if 'parts' in payload:
            # Multipart message - find text/plain or text/html
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    # Fallback to HTML if no plain text
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

        return ""
