"""
Unit tests for transaction categorization.
Tests cover category inference from merchant names and transaction types.
"""
from app.transactions.categorization import infer_category
from app.db.models import TransactionCategory


class TestCategorization:
    """Test suite for transaction categorization."""

    def test_dining_category(self):
        """Test dining & restaurant categorization."""
        category, confidence = infer_category("Starbucks", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        category, confidence = infer_category("McDonald's", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        category, confidence = infer_category("Blue Bottle Coffee", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        category, confidence = infer_category("Fancy Restaurant", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        category, confidence = infer_category("Chipotle Mexican Grill", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        category, confidence = infer_category("Panera Bread", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        category, confidence = infer_category("Pizza Hut", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        category, confidence = infer_category("Uber Eats", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        category, confidence = infer_category("DoorDash", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

    def test_groceries_category(self):
        """Test groceries categorization."""
        category, confidence = infer_category("Whole Foods", "purchase")
        assert category == TransactionCategory.GROCERIES
        assert confidence >= 90.0

        category, confidence = infer_category("Trader Joe's", "purchase")
        assert category == TransactionCategory.GROCERIES
        assert confidence >= 90.0

        category, confidence = infer_category("Safeway", "purchase")
        assert category == TransactionCategory.GROCERIES
        assert confidence >= 90.0

        category, confidence = infer_category("Kroger", "purchase")
        assert category == TransactionCategory.GROCERIES
        assert confidence >= 90.0

        category, confidence = infer_category("Costco", "purchase")
        assert category == TransactionCategory.GROCERIES
        assert confidence >= 90.0

        category, confidence = infer_category("Walmart Supercenter", "purchase")
        assert category == TransactionCategory.GROCERIES
        assert confidence >= 90.0

    def test_gas_category(self):
        """Test gas & fuel categorization."""
        category, confidence = infer_category("Shell Gas", "purchase")
        assert category == TransactionCategory.GAS
        assert confidence >= 90.0

        category, confidence = infer_category("Chevron", "purchase")
        assert category == TransactionCategory.GAS
        assert confidence >= 90.0

        category, confidence = infer_category("ExxonMobil", "purchase")
        assert category == TransactionCategory.GAS
        assert confidence >= 90.0

        category, confidence = infer_category("BP Gas Station", "purchase")
        assert category == TransactionCategory.GAS
        assert confidence >= 90.0

        category, confidence = infer_category("Costco Gas", "purchase")
        assert category == TransactionCategory.GAS
        assert confidence >= 90.0

    def test_travel_category(self):
        """Test travel categorization."""
        category, confidence = infer_category("United Airlines", "purchase")
        assert category == TransactionCategory.TRAVEL
        assert confidence >= 90.0

        category, confidence = infer_category("Delta Airlines", "purchase")
        assert category == TransactionCategory.TRAVEL
        assert confidence >= 90.0

        category, confidence = infer_category("Marriott", "purchase")
        assert category == TransactionCategory.TRAVEL
        assert confidence >= 90.0

        category, confidence = infer_category("Hilton Hotels", "purchase")
        assert category == TransactionCategory.TRAVEL
        assert confidence >= 90.0

        category, confidence = infer_category("Airbnb", "purchase")
        assert category == TransactionCategory.TRAVEL
        assert confidence >= 90.0

        category, confidence = infer_category("Hertz Car Rental", "purchase")
        assert category == TransactionCategory.TRAVEL
        assert confidence >= 90.0

        category, confidence = infer_category("Uber", "purchase")
        assert category == TransactionCategory.TRAVEL
        assert confidence >= 90.0

        category, confidence = infer_category("Lyft", "purchase")
        assert category == TransactionCategory.TRAVEL
        assert confidence >= 90.0

    def test_shopping_category(self):
        """Test shopping categorization."""
        category, confidence = infer_category("Amazon", "purchase")
        assert category == TransactionCategory.SHOPPING
        assert confidence >= 90.0

        category, confidence = infer_category("Target", "purchase")
        assert category == TransactionCategory.SHOPPING
        assert confidence >= 90.0

        category, confidence = infer_category("Best Buy", "purchase")
        assert category == TransactionCategory.SHOPPING
        assert confidence >= 90.0

        category, confidence = infer_category("The Home Depot", "purchase")
        assert category == TransactionCategory.SHOPPING
        assert confidence >= 90.0

        category, confidence = infer_category("Lowe's", "purchase")
        assert category == TransactionCategory.SHOPPING
        assert confidence >= 90.0

        category, confidence = infer_category("Apple Store", "purchase")
        assert category == TransactionCategory.SHOPPING
        assert confidence >= 90.0

        category, confidence = infer_category("Etsy", "purchase")
        assert category == TransactionCategory.SHOPPING
        assert confidence >= 90.0

    def test_entertainment_category(self):
        """Test entertainment categorization."""
        category, confidence = infer_category("Netflix", "purchase")
        assert category == TransactionCategory.ENTERTAINMENT
        assert confidence >= 90.0

        category, confidence = infer_category("Spotify", "purchase")
        assert category == TransactionCategory.ENTERTAINMENT
        assert confidence >= 90.0

        category, confidence = infer_category("Hulu", "purchase")
        assert category == TransactionCategory.ENTERTAINMENT
        assert confidence >= 90.0

        category, confidence = infer_category("HBO Max", "purchase")
        assert category == TransactionCategory.ENTERTAINMENT
        assert confidence >= 90.0

        category, confidence = infer_category("AMC Theatres", "purchase")
        assert category == TransactionCategory.ENTERTAINMENT
        assert confidence >= 90.0

        category, confidence = infer_category("Ticketmaster", "purchase")
        assert category == TransactionCategory.ENTERTAINMENT
        assert confidence >= 90.0

        category, confidence = infer_category("Steam Games", "purchase")
        assert category == TransactionCategory.ENTERTAINMENT
        assert confidence >= 90.0

        category, confidence = infer_category("Gym Membership", "purchase")
        assert category == TransactionCategory.ENTERTAINMENT
        assert confidence >= 90.0

    def test_utilities_category(self):
        """Test utilities categorization."""
        category, confidence = infer_category("PG&E Electric", "purchase")
        assert category == TransactionCategory.UTILITIES
        assert confidence >= 90.0

        category, confidence = infer_category("Comcast Internet", "purchase")
        assert category == TransactionCategory.UTILITIES
        assert confidence >= 90.0

        category, confidence = infer_category("Xfinity Cable", "purchase")
        assert category == TransactionCategory.UTILITIES
        assert confidence >= 90.0

        category, confidence = infer_category("AT&T Phone Bill", "purchase")
        assert category == TransactionCategory.UTILITIES
        assert confidence >= 90.0

        category, confidence = infer_category("Verizon Wireless", "purchase")
        assert category == TransactionCategory.UTILITIES
        assert confidence >= 90.0

    def test_healthcare_category(self):
        """Test healthcare categorization."""
        category, confidence = infer_category("CVS Pharmacy", "purchase")
        assert category == TransactionCategory.HEALTHCARE
        assert confidence >= 90.0

        category, confidence = infer_category("Walgreens", "purchase")
        assert category == TransactionCategory.HEALTHCARE
        assert confidence >= 90.0

        category, confidence = infer_category("Doctor's Office", "purchase")
        assert category == TransactionCategory.HEALTHCARE
        assert confidence >= 90.0

        category, confidence = infer_category("Dental Clinic", "purchase")
        assert category == TransactionCategory.HEALTHCARE
        assert confidence >= 90.0

        category, confidence = infer_category("Eye Care Center", "purchase")
        assert category == TransactionCategory.HEALTHCARE
        assert confidence >= 90.0

    def test_transportation_category(self):
        """Test transportation categorization."""
        category, confidence = infer_category("Parking Meter", "purchase")
        assert category == TransactionCategory.TRANSPORTATION
        assert confidence >= 90.0

        category, confidence = infer_category("Highway Toll", "purchase")
        assert category == TransactionCategory.TRANSPORTATION
        assert confidence >= 90.0

        category, confidence = infer_category("Metro Transit", "purchase")
        assert category == TransactionCategory.TRANSPORTATION
        assert confidence >= 90.0

        category, confidence = infer_category("BART Station", "purchase")
        assert category == TransactionCategory.TRANSPORTATION
        assert confidence >= 90.0

        category, confidence = infer_category("Amtrak Train", "purchase")
        assert category == TransactionCategory.TRANSPORTATION
        assert confidence >= 90.0

    def test_personal_care_category(self):
        """Test personal care categorization."""
        category, confidence = infer_category("Hair Salon", "purchase")
        assert category == TransactionCategory.PERSONAL_CARE
        assert confidence >= 90.0

        category, confidence = infer_category("Barber Shop", "purchase")
        assert category == TransactionCategory.PERSONAL_CARE
        assert confidence >= 90.0

        category, confidence = infer_category("Spa & Massage", "purchase")
        assert category == TransactionCategory.PERSONAL_CARE
        assert confidence >= 90.0

        category, confidence = infer_category("Nail Salon", "purchase")
        assert category == TransactionCategory.PERSONAL_CARE
        assert confidence >= 90.0

        category, confidence = infer_category("Sephora", "purchase")
        assert category == TransactionCategory.PERSONAL_CARE
        assert confidence >= 90.0

        category, confidence = infer_category("Dry Cleaning", "purchase")
        assert category == TransactionCategory.PERSONAL_CARE
        assert confidence >= 90.0

    def test_home_category(self):
        """Test home & garden categorization."""
        category, confidence = infer_category("Rent Payment", "purchase")
        assert category == TransactionCategory.HOME
        assert confidence >= 90.0

        category, confidence = infer_category("Mortgage Payment", "purchase")
        assert category == TransactionCategory.HOME
        assert confidence >= 90.0

        category, confidence = infer_category("IKEA Furniture", "purchase")
        assert category == TransactionCategory.HOME
        assert confidence >= 90.0

        category, confidence = infer_category("Wayfair Home Goods", "purchase")
        assert category == TransactionCategory.HOME
        assert confidence >= 90.0

        category, confidence = infer_category("Garden Nursery", "purchase")
        assert category == TransactionCategory.HOME
        assert confidence >= 90.0

    def test_education_category(self):
        """Test education categorization."""
        category, confidence = infer_category("University Tuition", "purchase")
        assert category == TransactionCategory.EDUCATION
        assert confidence >= 90.0

        category, confidence = infer_category("School Fee Payment", "purchase")
        assert category == TransactionCategory.EDUCATION
        assert confidence >= 90.0

        category, confidence = infer_category("Udemy Course", "purchase")
        assert category == TransactionCategory.EDUCATION
        assert confidence >= 90.0

        category, confidence = infer_category("Coursera Subscription", "purchase")
        assert category == TransactionCategory.EDUCATION
        assert confidence >= 90.0

    def test_transfer_category_by_type(self):
        """Test transfer category based on transaction type."""
        category, confidence = infer_category("Venmo", "transfer")
        assert category == TransactionCategory.TRANSFER
        assert confidence >= 90.0

        category, confidence = infer_category("Zelle Transfer", "transfer")
        assert category == TransactionCategory.TRANSFER
        assert confidence >= 90.0

        category, confidence = infer_category("Unknown Merchant", "transfer")
        assert category == TransactionCategory.TRANSFER
        assert confidence >= 90.0

    def test_payment_category_by_type(self):
        """Test payment category based on transaction type."""
        category, confidence = infer_category("Credit Card Payment", "payment")
        assert category == TransactionCategory.PAYMENT
        assert confidence >= 85.0

        category, confidence = infer_category("Bill Payment", "payment")
        assert category == TransactionCategory.PAYMENT
        assert confidence >= 85.0

    def test_other_category_fallback(self):
        """Test fallback to OTHER category for unknown merchants."""
        category, confidence = infer_category("Unknown Store", "purchase")
        assert category == TransactionCategory.OTHER
        assert confidence == 50.0

        category, confidence = infer_category("Random Merchant XYZ", "purchase")
        assert category == TransactionCategory.OTHER
        assert confidence == 50.0

        category, confidence = infer_category("New Local Business", "purchase")
        assert category == TransactionCategory.OTHER
        assert confidence == 50.0

    def test_case_insensitivity(self):
        """Test that categorization is case-insensitive."""
        category1, _ = infer_category("STARBUCKS", "purchase")
        category2, _ = infer_category("starbucks", "purchase")
        category3, _ = infer_category("StArBuCkS", "purchase")
        assert category1 == category2 == category3 == TransactionCategory.DINING

    def test_partial_matches(self):
        """Test that partial keyword matches work."""
        # "coffee" in name
        category, confidence = infer_category("Local Coffee House", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        # "restaurant" in name
        category, confidence = infer_category("Italian Restaurant Downtown", "purchase")
        assert category == TransactionCategory.DINING
        assert confidence >= 90.0

        # "market" in name
        category, confidence = infer_category("Farmer's Market", "purchase")
        assert category == TransactionCategory.GROCERIES
        assert confidence >= 90.0

    def test_confidence_scores(self):
        """Test that confidence scores are in valid range."""
        # High confidence (pattern match)
        _, confidence = infer_category("Starbucks", "purchase")
        assert 90.0 <= confidence <= 100.0

        # Medium confidence (transfer by type)
        _, confidence = infer_category("Venmo", "transfer")
        assert 85.0 <= confidence <= 100.0

        # Low confidence (unknown merchant)
        _, confidence = infer_category("Unknown Store", "purchase")
        assert 0.0 <= confidence < 70.0