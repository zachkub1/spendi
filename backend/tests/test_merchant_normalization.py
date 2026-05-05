"""
Unit tests for merchant name normalization.
Tests cover known patterns, edge cases, and cleanup logic.
"""
from app.transactions.merchant_normalization import normalize_merchant_name


class TestMerchantNormalization:
    """Test suite for merchant name normalization."""

    def test_square_patterns(self):
        """Test Square merchant patterns."""
        assert normalize_merchant_name("SQ *COFFEE SHOP") == "Square"
        assert normalize_merchant_name("SQUARE *BAKERY") == "Square"
        assert normalize_merchant_name("SQ*RESTAURANT") == "Square"

    def test_amazon_patterns(self):
        """Test Amazon merchant patterns."""
        assert normalize_merchant_name("AMZN MKTP US*AB12CD34") == "Amazon"
        assert normalize_merchant_name("AMZN.COM*123XYZ") == "Amazon"
        assert normalize_merchant_name("AMAZON.COM PURCHASE") == "Amazon"
        assert normalize_merchant_name("PRIME VIDEO*MONTHLY") == "Amazon Prime Video"
        assert normalize_merchant_name("AMZN DIGITAL*EBOOK") == "Amazon Digital"

    def test_uber_lyft_patterns(self):
        """Test ride-sharing patterns."""
        assert normalize_merchant_name("UBER TRIP HELP.UBER.COM") == "Uber"
        assert normalize_merchant_name("UBER EATS *ORDER") == "Uber Eats"
        assert normalize_merchant_name("UBER*TRIP") == "Uber"
        assert normalize_merchant_name("LYFT *RIDE 02-10") == "Lyft"

    def test_starbucks_patterns(self):
        """Test Starbucks patterns."""
        assert normalize_merchant_name("STARBUCKS 12345") == "Starbucks"
        assert normalize_merchant_name("STARBUCKS 00987") == "Starbucks"
        assert normalize_merchant_name("SBUX") == "Starbucks"

    def test_mcdonalds_patterns(self):
        """Test McDonald's patterns."""
        assert normalize_merchant_name("MCD 5678") == "McDonald's"
        assert normalize_merchant_name("MCDONALDS F12345") == "McDonald's"

    def test_walmart_target_patterns(self):
        """Test big box store patterns."""
        assert normalize_merchant_name("WALMART #1234") == "Walmart"
        assert normalize_merchant_name("WALMART 5678") == "Walmart"
        assert normalize_merchant_name("WAL-MART SUPERCENTER") == "Walmart"
        assert normalize_merchant_name("WM SUPERCENTER #123") == "Walmart"
        assert normalize_merchant_name("TARGET 9876") == "Target"
        assert normalize_merchant_name("TGT*STORE") == "Target"

    def test_costco_patterns(self):
        """Test Costco patterns."""
        assert normalize_merchant_name("COSTCO GAS #123") == "Costco Gas"
        assert normalize_merchant_name("COSTCO WHR #456") == "Costco"
        assert normalize_merchant_name("COSTCO WHSE #789") == "Costco"

    def test_gas_station_patterns(self):
        """Test gas station patterns."""
        assert normalize_merchant_name("SHELL OIL 12345") == "Shell Gas"
        assert normalize_merchant_name("SHELL 67890") == "Shell Gas"
        assert normalize_merchant_name("CHEVRON 11111") == "Chevron"
        assert normalize_merchant_name("CHEVRON*STATION") == "Chevron"
        assert normalize_merchant_name("BP #2222") == "BP Gas"
        assert normalize_merchant_name("EXXONMOBIL 3333") == "ExxonMobil"

    def test_grocery_store_patterns(self):
        """Test grocery store patterns."""
        assert normalize_merchant_name("WFM 5555") == "Whole Foods"
        assert normalize_merchant_name("WHOLE FOODS MARKET") == "Whole Foods"
        assert normalize_merchant_name("TRADER JOE'S #123") == "Trader Joe's"
        assert normalize_merchant_name("TJS STORE") == "Trader Joe's"
        assert normalize_merchant_name("SAFEWAY 9999") == "Safeway"
        assert normalize_merchant_name("KROGER 8888") == "Kroger"

    def test_tech_patterns(self):
        """Test technology company patterns."""
        assert normalize_merchant_name("APPLE.COM/BILL") == "Apple"
        assert normalize_merchant_name("APPLE STORE PURCHASE") == "Apple Store"

    def test_streaming_patterns(self):
        """Test streaming service patterns."""
        assert normalize_merchant_name("NETFLIX.COM SUBSCRIPTION") == "Netflix"
        assert normalize_merchant_name("SPOTIFY PREMIUM") == "Spotify"
        assert normalize_merchant_name("HULU MONTHLY") == "Hulu"
        assert normalize_merchant_name("HBO MAX SUBSCRIPTION") == "HBO Max"
        assert normalize_merchant_name("DISNEY+") == "Disney+"
        assert normalize_merchant_name("YOUTUBE PREMIUM") == "YouTube Premium"

    def test_p2p_patterns(self):
        """Test P2P payment patterns."""
        assert normalize_merchant_name("VENMO *PAYMENT") == "Venmo"
        assert normalize_merchant_name("ZELLE TRANSFER FROM JOHN") == "Zelle Transfer"
        assert normalize_merchant_name("ZELLE FROM SARAH") == "Zelle Transfer"
        assert normalize_merchant_name("CASH APP*PAYMENT") == "Cash App"
        assert normalize_merchant_name("PAYPAL *JOHN DOE") == "PayPal"

    def test_airline_patterns(self):
        """Test airline patterns."""
        assert normalize_merchant_name("UNITED AIR 0123456789") == "United Airlines"
        assert normalize_merchant_name("DELTA AIR 9876543210") == "Delta Airlines"
        assert normalize_merchant_name("SOUTHWEST AIR TICKET") == "Southwest Airlines"
        assert normalize_merchant_name("AMERICAN AIR FLIGHT") == "American Airlines"
        assert normalize_merchant_name("JETBLUE AIRWAYS") == "JetBlue"
        assert normalize_merchant_name("ALASKA AIR GROUP") == "Alaska Airlines"

    def test_hotel_patterns(self):
        """Test hotel patterns."""
        assert normalize_merchant_name("MARRIOTT HOTEL") == "Marriott"
        assert normalize_merchant_name("HILTON HOTELS") == "Hilton"
        assert normalize_merchant_name("HYATT REGENCY") == "Hyatt"
        assert normalize_merchant_name("AIRBNB BOOKING") == "Airbnb"

    def test_fast_food_patterns(self):
        """Test fast food patterns."""
        assert normalize_merchant_name("CHICK-FIL-A #123") == "Chick-fil-A"
        assert normalize_merchant_name("CHIPOTLE MEXICAN GRILL") == "Chipotle"
        assert normalize_merchant_name("PANERA BREAD") == "Panera Bread"
        assert normalize_merchant_name("SUBWAY #456") == "Subway"
        assert normalize_merchant_name("TACO BELL #789") == "Taco Bell"
        assert normalize_merchant_name("KFC RESTAURANT") == "KFC"
        assert normalize_merchant_name("BURGER KING #111") == "Burger King"
        assert normalize_merchant_name("WENDYS #222") == "Wendy's"

    def test_pharmacy_patterns(self):
        """Test pharmacy patterns."""
        assert normalize_merchant_name("CVS/PHARMACY #333") == "CVS Pharmacy"
        assert normalize_merchant_name("CVS 1234") == "CVS Pharmacy"
        assert normalize_merchant_name("WALGREENS #444") == "Walgreens"
        assert normalize_merchant_name("RITE AID PHARMACY") == "Rite Aid"

    def test_home_improvement_patterns(self):
        """Test home improvement store patterns."""
        assert normalize_merchant_name("HOME DEPOT #555") == "The Home Depot"
        assert normalize_merchant_name("LOWES #666") == "Lowe's"
        assert normalize_merchant_name("LOWE'S HOME IMPROVEMENT") == "Lowe's"

    def test_best_buy_patterns(self):
        """Test Best Buy patterns."""
        assert normalize_merchant_name("BEST BUY #777") == "Best Buy"
        assert normalize_merchant_name("BBY*PURCHASE") == "Best Buy"

    def test_pos_online_cleanup(self):
        """Test POS/ONLINE suffix removal."""
        assert normalize_merchant_name("COFFEE SHOP - POS") == "Coffee Shop"
        assert normalize_merchant_name("RESTAURANT ABC - ONLINE") == "Restaurant Abc"
        assert normalize_merchant_name("STORE XYZ POS") == "Store Xyz"
        assert normalize_merchant_name("MERCHANT - TEMP AUTH") == "Merchant"

    def test_location_suffix_cleanup(self):
        """Test location suffix removal."""
        assert normalize_merchant_name("COFFEE SHOP STORE #123") == "Coffee Shop"
        assert normalize_merchant_name("RESTAURANT LOCATION 456") == "Restaurant"
        assert normalize_merchant_name("BAKERY LOC789") == "Bakery"
        assert normalize_merchant_name("STORE BRANCH #999") == "Store"

    def test_city_state_cleanup(self):
        """Test city/state suffix removal."""
        assert normalize_merchant_name("RESTAURANT - NEW YORK NY") == "Restaurant"
        assert normalize_merchant_name("COFFEE SHOP - SAN FRANCISCO CA") == "Coffee Shop"
        assert normalize_merchant_name("BAKERY - LOS ANGELES CA") == "Bakery"

    def test_transaction_code_cleanup(self):
        """Test transaction code removal."""
        assert normalize_merchant_name("MERCHANT #ABC123") == "Merchant"
        assert normalize_merchant_name("STORE *XYZ789") == "Store"

    def test_store_id_cleanup(self):
        """Test store ID removal."""
        assert normalize_merchant_name("MERCHANT NAME 12345") == "Merchant Name"
        # Note: "LOCAL STORE 678901" has "STORE" keyword removed first (location suffix)
        assert normalize_merchant_name("LOCAL CAFE 678901") == "Local Cafe"

    def test_corporate_suffix_cleanup(self):
        """Test corporate suffix removal."""
        assert normalize_merchant_name("COMPANY NAME INC") == "Company Name"
        assert normalize_merchant_name("BUSINESS LLC") == "Business"
        assert normalize_merchant_name("STORE LTD") == "Store"
        assert normalize_merchant_name("MERCHANT CORP") == "Merchant"
        assert normalize_merchant_name("SHOP CO") == "Shop"

    def test_title_case_conversion(self):
        """Test title case conversion for unknown merchants."""
        assert normalize_merchant_name("UNKNOWN MERCHANT") == "Unknown Merchant"
        assert normalize_merchant_name("local coffee shop") == "Local Coffee Shop"
        assert normalize_merchant_name("RANDOM STORE NAME") == "Random Store Name"

    def test_whitespace_cleanup(self):
        """Test extra whitespace removal."""
        assert normalize_merchant_name("STORE    NAME") == "Store Name"
        assert normalize_merchant_name("  MERCHANT  ") == "Merchant"
        assert normalize_merchant_name("MULTIPLE   SPACES   HERE") == "Multiple Spaces Here"

    def test_empty_string_handling(self):
        """Test edge case: empty or whitespace-only strings."""
        assert normalize_merchant_name("") == ""
        assert normalize_merchant_name("   ") == ""

    def test_special_characters(self):
        """Test merchants with special characters."""
        # Note: "& CO" at the end will have "CO" removed as corporate suffix
        assert normalize_merchant_name("MERCHANT & COMPANY") == "Merchant & Company"
        assert normalize_merchant_name("MERCHANT #123 ABC") == "Merchant Abc"
        assert normalize_merchant_name("CAFÉ BISTRO") == "Café Bistro"

    def test_combined_cleanup(self):
        """Test multiple cleanup rules applied together."""
        # POS + Store ID + Location
        result = normalize_merchant_name("RESTAURANT ABC STORE #123 - SAN JOSE CA - POS")
        assert result == "Restaurant Abc"

        # Transaction code + Corp suffix (store ID with fewer than 4 digits stays)
        result = normalize_merchant_name("MERCHANT NAME #XYZ789 INC")
        assert result == "Merchant Name"

        # Online + Location + Whitespace
        result = normalize_merchant_name("LOCAL   SHOP   LOCATION 456 - ONLINE")
        assert result == "Local Shop"