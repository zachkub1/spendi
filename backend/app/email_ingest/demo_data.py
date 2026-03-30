"""
Demo email dataset for testing the email parsing pipeline without real Gmail access.

Each entry is crafted to exactly match the regex patterns of a specific parser.
Emails with parseable=False are intentionally non-transactional (no parser will match).
"""
from datetime import datetime, timezone

DEMO_EMAILS = [
    # ── Chase (3 transactional) ───────────────────────────────────────────────
    # SENDER_PATTERN : @chase\.com$ | @alerts\.chase\.com$
    # SUBJECT_PATTERN: Your \$[\d,]+\.\d{2} transaction
    # MERCHANT_PATTERN: transaction at (.+?) on   (in body)
    # DATE_PATTERN   : on (\d{2}/\d{2}/\d{4})    (in body)
    # CARD_PATTERN   : ending in (\d{4})          (in body)
    {
        "message_id": "demo_chase_001",
        "parseable": True,
        "from": "no.reply.alerts@chase.com",
        "subject": "Your $6.50 transaction",
        "body": (
            "A transaction has been made on your Chase card.\n"
            "transaction at Starbucks on 03/10/2026.\n"
            "Card ending in 4242."
        ),
        "received_at": datetime(2026, 3, 10, 9, 15, 0, tzinfo=timezone.utc),
    },
    {
        "message_id": "demo_chase_002",
        "parseable": True,
        "from": "no.reply.alerts@chase.com",
        "subject": "Your $89.99 transaction",
        "body": (
            "A transaction has been made on your Chase card.\n"
            "transaction at Amazon on 03/12/2026.\n"
            "Card ending in 4242."
        ),
        "received_at": datetime(2026, 3, 12, 14, 30, 0, tzinfo=timezone.utc),
    },
    {
        "message_id": "demo_chase_003",
        "parseable": True,
        "from": "no.reply.alerts@chase.com",
        "subject": "Your $67.23 transaction",
        "body": (
            "A transaction has been made on your Chase card.\n"
            "transaction at Whole Foods Market on 03/18/2026.\n"
            "Card ending in 4242."
        ),
        "received_at": datetime(2026, 3, 18, 17, 45, 0, tzinfo=timezone.utc),
    },

    # ── American Express (2 transactional) ────────────────────────────────────
    # SENDER_PATTERN : @(?:[\w-]+\.)?americanexpress\.com$
    # SUBJECT_PATTERN: Charge of \$[\d,]+\.\d{2}
    # MERCHANT_PATTERN: at (.+?) has been approved  (in body)
    # DATE_PATTERN   : on (\d{2}/\d{2}/\d{4})      (in body)
    # CARD_PATTERN   : ending in (\d{4})            (in body)
    {
        "message_id": "demo_amex_001",
        "parseable": True,
        "from": "AmericanExpress@welcome.americanexpress.com",
        "subject": "Charge of $342.00 on Your Account",
        "body": (
            "Dear Cardmember,\n"
            "A charge of $342.00 was made at Delta Air Lines has been approved "
            "on 03/14/2026.\n"
            "Card ending in 9876."
        ),
        "received_at": datetime(2026, 3, 14, 11, 0, 0, tzinfo=timezone.utc),
    },
    {
        "message_id": "demo_amex_002",
        "parseable": True,
        "from": "AmericanExpress@welcome.americanexpress.com",
        "subject": "Charge of $156.75 on Your Account",
        "body": (
            "Dear Cardmember,\n"
            "A charge of $156.75 was made at Marriott Hotels has been approved "
            "on 03/20/2026.\n"
            "Card ending in 9876."
        ),
        "received_at": datetime(2026, 3, 20, 15, 30, 0, tzinfo=timezone.utc),
    },

    # ── Discover (1 transactional) ────────────────────────────────────────────
    # SENDER_PATTERN  : @services\.discover\.com$
    # SUBJECT_PATTERNS: "Transaction Alert" matches first pattern
    # AMOUNT_PATTERN  : \$([\d,]+\.\d{2})          (falls back to body)
    # MERCHANT_PATTERN: (?:at|merchant:|to)\s+([A-Z]...) (?:\s+on|...)
    # DATE_PATTERNS   : on (\d{1,2}/\d{1,2}/\d{4})
    # CARD_PATTERN    : xxxx(\d{4})
    {
        "message_id": "demo_discover_001",
        "parseable": True,
        "from": "discover@services.discover.com",
        "subject": "Transaction Alert",
        "body": (
            "A purchase was made on your Discover card.\n"
            "Amount: $43.29\n"
            "at Target on 03/16/2026.\n"
            "Card xxxx5555."
        ),
        "received_at": datetime(2026, 3, 16, 13, 20, 0, tzinfo=timezone.utc),
    },

    # ── Venmo (2 transactional) ───────────────────────────────────────────────
    # SENDER_PATTERN      : @venmo\.com$
    # SUBJECT_PATTERN     : You paid
    # AMOUNT_PATTERN      : \$([\d,]+\.\d{2})  (from subject)
    # PERSON_PAID_PATTERN : You paid ([^\$]+) \$
    {
        "message_id": "demo_venmo_001",
        "parseable": True,
        "from": "venmo@venmo.com",
        "subject": "You paid Mike $45.00",
        "body": "You paid Mike $45.00 for dinner.",
        "received_at": datetime(2026, 3, 22, 20, 0, 0, tzinfo=timezone.utc),
    },
    {
        "message_id": "demo_venmo_002",
        "parseable": True,
        "from": "venmo@venmo.com",
        "subject": "You paid Sarah $120.00",
        "body": "You paid Sarah $120.00 for rent split.",
        "received_at": datetime(2026, 3, 25, 10, 0, 0, tzinfo=timezone.utc),
    },

    # ── Zelle (1 transactional) ───────────────────────────────────────────────
    # SENDER_PATTERN      : @zellepay\.com$
    # SUBJECT_PATTERN     : sent you
    # AMOUNT_PATTERN      : \$([\d,]+\.\d{2})  (from subject)
    # PERSON_SENT_PATTERN : ([^\s]+) sent you   (matches first word only)
    {
        "message_id": "demo_zelle_001",
        "parseable": True,
        "from": "notify@zellepay.com",
        "subject": "David sent you $200.00",
        "body": "David sent you $200.00 with Zelle.",
        "received_at": datetime(2026, 3, 28, 16, 0, 0, tzinfo=timezone.utc),
    },

    # ── Non-transactional (3) ─────────────────────────────────────────────────
    # Sender domains are recognized but subjects don't match any parser's
    # SUBJECT_PATTERN, so ParserRegistry.get_parser() returns None.
    # These are stored as RawEmails with parsing_status="non_transaction".
    {
        "message_id": "demo_nontxn_001",
        "parseable": False,
        "from": "no.reply.alerts@chase.com",
        "subject": "Your statement is ready",
        "body": "Your monthly statement is now available. Log in to view it.",
        "received_at": datetime(2026, 3, 5, 8, 0, 0, tzinfo=timezone.utc),
    },
    {
        "message_id": "demo_nontxn_002",
        "parseable": False,
        "from": "AmericanExpress@welcome.americanexpress.com",
        "subject": "Exclusive offers for Cardmembers",
        "body": "Discover exclusive deals and offers for your American Express card.",
        "received_at": datetime(2026, 3, 8, 9, 0, 0, tzinfo=timezone.utc),
    },
    {
        "message_id": "demo_nontxn_003",
        "parseable": False,
        "from": "discover@services.discover.com",
        "subject": "Your Cashback Bonus update",
        "body": "Your Cashback Bonus balance has been updated. Check your rewards.",
        "received_at": datetime(2026, 3, 11, 10, 0, 0, tzinfo=timezone.utc),
    },
]
