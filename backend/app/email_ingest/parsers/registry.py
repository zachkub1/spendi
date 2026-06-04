"""
Parser registry - routes emails to appropriate parsers.
"""
from typing import Optional
from .base import EmailParser
from .chase import ChaseParser
from .amex import AmexParser
from .venmo import VenmoParser
from .zelle import ZelleParser
from .discover import DiscoverParser
from .republictt import RepublicTTParser


class ParserRegistry:
    """Central registry for email parsers."""

    parsers: list[EmailParser] = [
        ChaseParser(),
        AmexParser(),
        VenmoParser(),
        ZelleParser(),
        DiscoverParser(),
        RepublicTTParser(),
    ]

    @classmethod
    def get_parser(cls, sender: str, subject: str) -> Optional[EmailParser]:
        """
        Find appropriate parser for email.

        Args:
            sender: Email sender address
            subject: Email subject line

        Returns:
            EmailParser instance if match found, None otherwise
        """
        for parser in cls.parsers:
            if parser.can_parse(sender, subject):
                return parser
        return None

    @classmethod
    def get_allowed_senders(cls) -> list[str]:
        """
        Get list of sender domains for Gmail filter.

        Returns:
            List of sender domains (e.g., ["chase.com", "venmo.com"])
        """
        return [
            "chase.com",
            "alerts.chase.com",
            "americanexpress.com",
            "aexp.com",
            "venmo.com",
            "zellepay.com",
            "notify.zelle.com",
            "tdbank.com",
            "discover.com",
            "services.discover.com",
            "discovercard.com",
            "republictt.com",
        ]
