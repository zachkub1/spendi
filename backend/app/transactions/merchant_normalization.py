"""
Merchant name normalization service.
Converts raw merchant names from emails into standardized, human-readable names.
"""
import re
from typing import Dict, Pattern


# Merchant normalization rules (regex pattern -> normalized name)
MERCHANT_RULES: Dict[str, str] = {
    # Square
    r"SQ\s*\*": "Square",
    r"SQUARE\s*\*": "Square",

    # Amazon
    r"AMZN\s*MKTP": "Amazon",
    r"AMZN\.COM": "Amazon",
    r"AMAZON\.COM": "Amazon",
    r"PRIME VIDEO": "Amazon Prime Video",
    r"AMZN\s*DIGITAL": "Amazon Digital",

    # Uber/Lyft
    r"UBER\s*TRIP": "Uber",
    r"UBER\s*EATS": "Uber Eats",
    r"UBER\*TRIP": "Uber",
    r"UBER\s*\*": "Uber",
    r"LYFT\s*\*": "Lyft",

    # Starbucks
    r"STARBUCKS\s*\d+": "Starbucks",
    r"SBUX": "Starbucks",

    # McDonald's
    r"MCD\s*\d+": "McDonald's",
    r"MCDONALDS": "McDonald's",

    # Walmart
    r"WALMART\s*#?\d*": "Walmart",
    r"WAL-MART": "Walmart",
    r"WM\s*SUPERCENTER": "Walmart",

    # Target
    r"TARGET\s*\d+": "Target",
    r"TGT\*": "Target",

    # Costco
    r"COSTCO\s*GAS": "Costco Gas",
    r"COSTCO\s*WHR": "Costco",
    r"COSTCO\s*W+HS": "Costco",

    # Shell Gas
    r"SHELL\s*OIL": "Shell Gas",
    r"SHELL\s*\d+": "Shell Gas",

    # Chevron
    r"CHEVRON\s*\d+": "Chevron",
    r"CHEVRON\s*\*": "Chevron",

    # BP / Exxon / Mobil
    r"BP\s*\#?\d+": "BP Gas",
    r"EXXONMOBIL": "ExxonMobil",
    r"EXXON": "ExxonMobil",

    # Whole Foods
    r"WFM\s*\d+": "Whole Foods",
    r"WHOLE\s*FOODS": "Whole Foods",

    # Trader Joe's
    r"TRADER\s*JOE": "Trader Joe's",
    r"TJS": "Trader Joe's",

    # Safeway / Kroger
    r"SAFEWAY\s*\d+": "Safeway",
    r"KROGER\s*\d+": "Kroger",

    # Apple
    r"APPLE\.COM/BILL": "Apple",
    r"APPLE\s*STORE": "Apple Store",

    # Netflix/Spotify/Streaming
    r"NETFLIX\.COM": "Netflix",
    r"SPOTIFY": "Spotify",
    r"HULU": "Hulu",
    r"HBO\s*MAX": "HBO Max",
    r"DISNEY\+": "Disney+",
    r"YOUTUBE\s*PREMIUM": "YouTube Premium",

    # Venmo/Zelle (keep original names for P2P)
    r"VENMO\s*\*": "Venmo",
    r"ZELLE\s*TRANSFER": "Zelle Transfer",
    r"ZELLE\s*FROM": "Zelle Transfer",
    r"CASH\s*APP": "Cash App",
    r"PAYPAL\s*\*": "PayPal",

    # Airlines
    r"UNITED\s*AIR": "United Airlines",
    r"DELTA\s*AIR": "Delta Airlines",
    r"SOUTHWEST\s*AIR": "Southwest Airlines",
    r"AMERICAN\s*AIR": "American Airlines",
    r"JETBLUE": "JetBlue",
    r"ALASKA\s*AIR": "Alaska Airlines",

    # Hotels
    r"MARRIOTT": "Marriott",
    r"HILTON": "Hilton",
    r"HYATT": "Hyatt",
    r"AIRBNB": "Airbnb",

    # Fast Food
    r"CHICK-FIL-A": "Chick-fil-A",
    r"CHIPOTLE": "Chipotle",
    r"PANERA": "Panera Bread",
    r"SUBWAY": "Subway",
    r"TACO\s*BELL": "Taco Bell",
    r"KFC": "KFC",
    r"BURGER\s*KING": "Burger King",
    r"WENDY'?S": "Wendy's",

    # Coffee Shops
    r"DUNKIN": "Dunkin'",
    r"PEET'?S\s*COFFEE": "Peet's Coffee",

    # Pharmacies
    r"CVS/PHARMACY": "CVS Pharmacy",
    r"CVS\s*\d+": "CVS Pharmacy",
    r"WALGREENS": "Walgreens",
    r"RITE\s*AID": "Rite Aid",

    # Home Improvement
    r"HOME\s*DEPOT": "The Home Depot",
    r"LOWE'?S": "Lowe's",

    # Best Buy
    r"BEST\s*BUY": "Best Buy",
    r"BBY\*": "Best Buy",
}

# Compile regex patterns for efficiency
COMPILED_RULES: Dict[Pattern, str] = {
    re.compile(pattern, re.IGNORECASE): normalized
    for pattern, normalized in MERCHANT_RULES.items()
}


def normalize_merchant_name(raw_merchant_name: str) -> str:
    """
    Normalize raw merchant name from email to human-readable format.

    Args:
        raw_merchant_name: Raw merchant name from email (e.g., "SQ *COFFEE SHOP")

    Returns:
        Normalized merchant name (e.g., "Square")

    Examples:
        >>> normalize_merchant_name("SQ *COFFEE SHOP")
        'Square'
        >>> normalize_merchant_name("AMZN MKTP US*AB12CD34")
        'Amazon'
        >>> normalize_merchant_name("STARBUCKS 12345")
        'Starbucks'
        >>> normalize_merchant_name("UNKNOWN MERCHANT INC")
        'Unknown Merchant Inc'
        >>> normalize_merchant_name("COFFEE SHOP #123 POS")
        'Coffee Shop'
        >>> normalize_merchant_name("RESTAURANT ABC - ONLINE")
        'Restaurant Abc'
    """
    # Try to match against known patterns
    for pattern, normalized_name in COMPILED_RULES.items():
        if pattern.search(raw_merchant_name):
            return normalized_name

    # If no match, apply basic cleanup
    # Remove common suffixes and clean up formatting
    cleaned = raw_merchant_name.strip()

    # Handle empty strings early
    if not cleaned:
        return ""

    # Remove POS/ONLINE/TEMP AUTH indicators
    cleaned = re.sub(r'\s*-?\s*(POS|ONLINE|TEMP\s*AUTH)\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\bPOS\b\s*', ' ', cleaned, flags=re.IGNORECASE)

    # Remove location suffixes (e.g., "STORE #123", "LOCATION 456")
    cleaned = re.sub(r'\s*(STORE|LOCATION|LOC|BRANCH)\s*#?\d+', '', cleaned, flags=re.IGNORECASE)

    # Remove city/state suffixes (e.g., "- NEW YORK NY", "- SAN FRANCISCO CA")
    cleaned = re.sub(r'\s*-\s*[A-Z\s]+\s+[A-Z]{2}\s*$', '', cleaned)

    # Remove transaction codes (e.g., "#12345", "*ABC123")
    cleaned = re.sub(r'[#*][A-Z0-9]+', '', cleaned, flags=re.IGNORECASE)

    # Remove trailing numbers (store IDs) - 4 or more digits
    cleaned = re.sub(r'\s+\d{4,}\s*$', '', cleaned)

    # Remove common abbreviations at end (but not in middle like "& CO")
    cleaned = re.sub(r'\s+(INC|LLC|LTD|CORP)\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+\bCO\b\s*$', '', cleaned, flags=re.IGNORECASE)

    # Convert to title case
    cleaned = cleaned.title()

    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned if cleaned else raw_merchant_name