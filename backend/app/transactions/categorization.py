"""
Transaction categorization service.
Infers spending categories from merchant names using rule-based logic.
"""
from typing import Tuple, Dict, List
import re

from app.db.models import TransactionCategory


# Merchant name patterns mapped to categories
# Format: category -> list of regex patterns
CATEGORY_RULES: Dict[TransactionCategory, List[str]] = {
    TransactionCategory.DINING: [
        r"restaurant",
        r"cafe|coffee",
        r"starbucks|sbux",
        r"mcdonald|mcd",
        r"burger|pizza|taco|subway",
        r"chipotle|panera",
        r"domino|papa john",
        r"doordash|uber\s*eats|grubhub",
        r"dining|eatery|bistro|grill",
        r"bar & grill|pub",
    ],

    TransactionCategory.GROCERIES: [
        r"grocery|market",
        r"whole foods|wfm",
        r"trader joe|tjs",
        r"safeway|kroger|publix",
        r"walmart.*superc",  # Walmart Supercenter
        r"target.*groc",
        r"costco(?!.*gas)|sam'?s club",
        r"aldi|lidl",
        r"sprouts|fresh market",
    ],

    TransactionCategory.GAS: [
        r"shell|chevron|exxon|mobil",
        r"bp |arco|valero|marathon",
        r"gas station|fuel|petroleum",
        r"costco.*gas",
        r"76 gas|circle k",
    ],

    TransactionCategory.TRAVEL: [
        r"airline|air travel|airways",
        r"united air|delta air|southwest|american air",
        r"hotel|motel|inn|resort",
        r"marriott|hilton|hyatt|sheraton",
        r"airbnb|vrbo",
        r"expedia|booking\.com|hotels\.com",
        r"car rental|hertz|enterprise|avis",
        r"uber(?!.*eats)|lyft",  # Ride-sharing, not food
        r"airport parking",
    ],

    TransactionCategory.SHOPPING: [
        r"amazon(?!.*prime video)",  # Amazon shopping, not video
        r"target(?!.*gas)",
        r"walmart(?!.*gas)",
        r"best buy|bestbuy",
        r"home depot|lowes|lowe's",
        r"macy's|nordstrom|kohl's",
        r"tj maxx|tjx|marshalls|ross",
        r"apple store|microsoft store",
        r"etsy|ebay",
    ],

    TransactionCategory.ENTERTAINMENT: [
        r"netflix|hulu|disney\+|hbo|prime video",
        r"spotify|apple music|pandora",
        r"movie|cinema|theater|theatre",
        r"amc theatres|regal cinema",
        r"ticketmaster|stubhub",
        r"steam|playstation|xbox|nintendo",
        r"gym|fitness|yoga|pilates",
        r"golf|bowling",
    ],

    TransactionCategory.UTILITIES: [
        r"electric|power|energy|pge|duke energy",
        r"water.*utility|water.*district",
        r"gas.*utility|natural gas",
        r"internet|cable|comcast|xfinity",
        r"at&t|verizon|t-mobile|sprint",
        r"phone.*bill",
    ],

    TransactionCategory.HEALTHCARE: [
        r"pharmacy|cvs|walgreens|rite aid",
        r"medical|doctor|clinic|hospital",
        r"dentist|dental",
        r"optometrist|eye care|vision",
        r"urgent care|emergency",
        r"health insurance|blue cross|kaiser",
    ],

    TransactionCategory.TRANSPORTATION: [
        r"parking|park meter",
        r"toll|fastrak|ezpass",
        r"public.*transit|metro|subway|bart",
        r"train|amtrak|rail",
        r"bus.*ticket",
        r"taxi(?!.*uber|lyft)",  # Traditional taxis
    ],

    TransactionCategory.PERSONAL_CARE: [
        r"salon|barber|haircut",
        r"spa|massage",
        r"nail.*salon|manicure",
        r"cosmetic|sephora|ulta",
        r"dry clean|laundry",
    ],

    TransactionCategory.HOME: [
        r"rent payment|lease",
        r"mortgage",
        r"homeowner.*assoc|hoa",
        r"furniture|ikea|wayfair",
        r"garden|nursery|plants",
        r"hardware|tools",
    ],

    TransactionCategory.EDUCATION: [
        r"tuition|college|university",
        r"school.*fee|education",
        r"textbook|course|class",
        r"udemy|coursera|skillshare",
    ],

    TransactionCategory.TRANSFER: [
        r"venmo|zelle|cashapp|paypal",
        r"transfer.*to|transfer.*from",
        r"p2p.*payment",
    ],

    TransactionCategory.PAYMENT: [
        r"payment.*thank you|autopay",
        r"bill.*payment|online payment",
        r"credit card.*payment",
    ],
}

# Compile patterns for efficiency
COMPILED_CATEGORY_RULES: Dict[TransactionCategory, List[re.Pattern]] = {
    category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for category, patterns in CATEGORY_RULES.items()
}


def infer_category(
    merchant_name: str,
    transaction_type: str
) -> Tuple[TransactionCategory, float]:
    """
    Infer transaction category from merchant name and transaction type.

    Args:
        merchant_name: Normalized merchant name
        transaction_type: Transaction type (purchase, refund, payment, transfer)

    Returns:
        Tuple of (category, confidence_score)
        Confidence score is 0-100, where:
        - 90-100: High confidence (exact match)
        - 70-89: Medium confidence (fuzzy match)
        - 0-69: Low confidence (default/fallback)

    Examples:
        >>> infer_category("Starbucks", "purchase")
        (TransactionCategory.DINING, 95.0)
        >>> infer_category("Venmo", "transfer")
        (TransactionCategory.TRANSFER, 90.0)
        >>> infer_category("Unknown Merchant", "purchase")
        (TransactionCategory.OTHER, 50.0)
    """
    # First, check transaction type for explicit categorization
    if transaction_type == "transfer":
        return (TransactionCategory.TRANSFER, 90.0)
    elif transaction_type == "payment":
        return (TransactionCategory.PAYMENT, 85.0)

    # Try to match merchant name against category rules
    for category, patterns in COMPILED_CATEGORY_RULES.items():
        for pattern in patterns:
            if pattern.search(merchant_name):
                # High confidence for pattern match
                return (category, 90.0)

    # No match found - return OTHER with low confidence
    return (TransactionCategory.OTHER, 50.0)


def get_category_display_name(category: TransactionCategory) -> str:
    """
    Get human-readable display name for category.

    Args:
        category: TransactionCategory enum value

    Returns:
        Display name (e.g., "Dining & Restaurants")
    """
    display_names = {
        TransactionCategory.DINING: "Dining & Restaurants",
        TransactionCategory.GROCERIES: "Groceries",
        TransactionCategory.GAS: "Gas & Fuel",
        TransactionCategory.TRAVEL: "Travel",
        TransactionCategory.SHOPPING: "Shopping",
        TransactionCategory.ENTERTAINMENT: "Entertainment",
        TransactionCategory.UTILITIES: "Utilities",
        TransactionCategory.HEALTHCARE: "Healthcare",
        TransactionCategory.TRANSPORTATION: "Transportation",
        TransactionCategory.PERSONAL_CARE: "Personal Care",
        TransactionCategory.HOME: "Home & Garden",
        TransactionCategory.EDUCATION: "Education",
        TransactionCategory.TRANSFER: "Transfers",
        TransactionCategory.PAYMENT: "Payments",
        TransactionCategory.OTHER: "Other",
    }
    return display_names.get(category, category.value.title())