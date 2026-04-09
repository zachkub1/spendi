"""
Category accuracy testing with labeled dataset.
Measures categorization accuracy against 100+ labeled transactions.
Target: ≥80% accuracy
"""
import pytest
from typing import List, Tuple
from app.transactions.categorization import infer_category
from app.db.models import TransactionCategory


# Labeled test dataset: (merchant_name, transaction_type, expected_category)
LABELED_DATASET: List[Tuple[str, str, TransactionCategory]] = [
    # Dining & Restaurants (20 samples)
    ("Starbucks", "purchase", TransactionCategory.DINING),
    ("McDonald's", "purchase", TransactionCategory.DINING),
    ("Chipotle", "purchase", TransactionCategory.DINING),
    ("Panera Bread", "purchase", TransactionCategory.DINING),
    ("Subway", "purchase", TransactionCategory.DINING),
    ("Taco Bell", "purchase", TransactionCategory.DINING),
    ("Pizza Hut", "purchase", TransactionCategory.DINING),
    ("Domino's Pizza", "purchase", TransactionCategory.DINING),
    ("KFC", "purchase", TransactionCategory.DINING),
    ("Burger King", "purchase", TransactionCategory.DINING),
    ("Wendy's", "purchase", TransactionCategory.DINING),
    ("Chick-fil-A", "purchase", TransactionCategory.DINING),
    ("Blue Bottle Coffee", "purchase", TransactionCategory.DINING),
    ("Peet's Coffee", "purchase", TransactionCategory.DINING),
    ("Dunkin'", "purchase", TransactionCategory.DINING),
    ("Uber Eats", "purchase", TransactionCategory.DINING),
    ("DoorDash", "purchase", TransactionCategory.DINING),
    ("Fancy Italian Restaurant", "purchase", TransactionCategory.DINING),
    ("Local Bistro Cafe", "purchase", TransactionCategory.DINING),
    ("Sushi Bar & Grill", "purchase", TransactionCategory.DINING),

    # Groceries (15 samples)
    ("Whole Foods", "purchase", TransactionCategory.GROCERIES),
    ("Trader Joe's", "purchase", TransactionCategory.GROCERIES),
    ("Safeway", "purchase", TransactionCategory.GROCERIES),
    ("Kroger", "purchase", TransactionCategory.GROCERIES),
    ("Costco", "purchase", TransactionCategory.GROCERIES),
    ("Sam's Club", "purchase", TransactionCategory.GROCERIES),
    ("Walmart Supercenter", "purchase", TransactionCategory.GROCERIES),
    ("Target Groceries", "purchase", TransactionCategory.GROCERIES),
    ("Aldi", "purchase", TransactionCategory.GROCERIES),
    ("Sprouts Farmers Market", "purchase", TransactionCategory.GROCERIES),
    ("Fresh Market", "purchase", TransactionCategory.GROCERIES),
    ("Publix", "purchase", TransactionCategory.GROCERIES),
    ("Grocery Outlet", "purchase", TransactionCategory.GROCERIES),
    ("Local Farmers Market", "purchase", TransactionCategory.GROCERIES),
    ("Organic Food Market", "purchase", TransactionCategory.GROCERIES),

    # Gas & Fuel (10 samples)
    ("Shell Gas", "purchase", TransactionCategory.GAS),
    ("Chevron", "purchase", TransactionCategory.GAS),
    ("ExxonMobil", "purchase", TransactionCategory.GAS),
    ("BP Gas Station", "purchase", TransactionCategory.GAS),
    ("Costco Gas", "purchase", TransactionCategory.GAS),
    ("Arco", "purchase", TransactionCategory.GAS),
    ("76 Gas Station", "purchase", TransactionCategory.GAS),
    ("Marathon Petroleum", "purchase", TransactionCategory.GAS),
    ("Valero", "purchase", TransactionCategory.GAS),
    ("Circle K Fuel", "purchase", TransactionCategory.GAS),

    # Travel (15 samples)
    ("United Airlines", "purchase", TransactionCategory.TRAVEL),
    ("Delta Airlines", "purchase", TransactionCategory.TRAVEL),
    ("Southwest Airlines", "purchase", TransactionCategory.TRAVEL),
    ("American Airlines", "purchase", TransactionCategory.TRAVEL),
    ("JetBlue", "purchase", TransactionCategory.TRAVEL),
    ("Alaska Airlines", "purchase", TransactionCategory.TRAVEL),
    ("Marriott", "purchase", TransactionCategory.TRAVEL),
    ("Hilton Hotels", "purchase", TransactionCategory.TRAVEL),
    ("Hyatt", "purchase", TransactionCategory.TRAVEL),
    ("Airbnb", "purchase", TransactionCategory.TRAVEL),
    ("Hertz Car Rental", "purchase", TransactionCategory.TRAVEL),
    ("Enterprise Rent-A-Car", "purchase", TransactionCategory.TRAVEL),
    ("Uber", "purchase", TransactionCategory.TRAVEL),
    ("Lyft", "purchase", TransactionCategory.TRAVEL),
    ("Airport Parking", "purchase", TransactionCategory.TRAVEL),

    # Shopping (15 samples)
    ("Amazon", "purchase", TransactionCategory.SHOPPING),
    ("Target", "purchase", TransactionCategory.SHOPPING),
    ("Walmart", "purchase", TransactionCategory.SHOPPING),
    ("Best Buy", "purchase", TransactionCategory.SHOPPING),
    ("The Home Depot", "purchase", TransactionCategory.SHOPPING),
    ("Lowe's", "purchase", TransactionCategory.SHOPPING),
    ("Apple Store", "purchase", TransactionCategory.SHOPPING),
    ("Macy's", "purchase", TransactionCategory.SHOPPING),
    ("Nordstrom", "purchase", TransactionCategory.SHOPPING),
    ("Kohl's", "purchase", TransactionCategory.SHOPPING),
    ("TJ Maxx", "purchase", TransactionCategory.SHOPPING),
    ("Ross Dress for Less", "purchase", TransactionCategory.SHOPPING),
    ("Etsy", "purchase", TransactionCategory.SHOPPING),
    ("eBay", "purchase", TransactionCategory.SHOPPING),
    ("Microsoft Store", "purchase", TransactionCategory.SHOPPING),

    # Entertainment (12 samples)
    ("Netflix", "purchase", TransactionCategory.ENTERTAINMENT),
    ("Spotify", "purchase", TransactionCategory.ENTERTAINMENT),
    ("Hulu", "purchase", TransactionCategory.ENTERTAINMENT),
    ("HBO Max", "purchase", TransactionCategory.ENTERTAINMENT),
    ("Disney+", "purchase", TransactionCategory.ENTERTAINMENT),
    ("YouTube Premium", "purchase", TransactionCategory.ENTERTAINMENT),
    ("AMC Theatres", "purchase", TransactionCategory.ENTERTAINMENT),
    ("Regal Cinemas", "purchase", TransactionCategory.ENTERTAINMENT),
    ("Ticketmaster", "purchase", TransactionCategory.ENTERTAINMENT),
    ("StubHub", "purchase", TransactionCategory.ENTERTAINMENT),
    ("Steam", "purchase", TransactionCategory.ENTERTAINMENT),
    ("PlayStation Store", "purchase", TransactionCategory.ENTERTAINMENT),

    # Utilities (8 samples)
    ("PG&E Electric", "purchase", TransactionCategory.UTILITIES),
    ("Duke Energy", "purchase", TransactionCategory.UTILITIES),
    ("Comcast Internet", "purchase", TransactionCategory.UTILITIES),
    ("Xfinity Cable", "purchase", TransactionCategory.UTILITIES),
    ("AT&T Phone Bill", "purchase", TransactionCategory.UTILITIES),
    ("Verizon Wireless", "purchase", TransactionCategory.UTILITIES),
    ("T-Mobile", "purchase", TransactionCategory.UTILITIES),
    ("Water Utility District", "purchase", TransactionCategory.UTILITIES),

    # Healthcare (8 samples)
    ("CVS Pharmacy", "purchase", TransactionCategory.HEALTHCARE),
    ("Walgreens", "purchase", TransactionCategory.HEALTHCARE),
    ("Rite Aid", "purchase", TransactionCategory.HEALTHCARE),
    ("Kaiser Permanente", "purchase", TransactionCategory.HEALTHCARE),
    ("Blue Cross Health Insurance", "purchase", TransactionCategory.HEALTHCARE),
    ("Medical Clinic", "purchase", TransactionCategory.HEALTHCARE),
    ("Dental Office", "purchase", TransactionCategory.HEALTHCARE),
    ("Eye Care Center", "purchase", TransactionCategory.HEALTHCARE),

    # Transportation (7 samples)
    ("Parking Meter", "purchase", TransactionCategory.TRANSPORTATION),
    ("Highway Toll", "purchase", TransactionCategory.TRANSPORTATION),
    ("FasTrak", "purchase", TransactionCategory.TRANSPORTATION),
    ("Metro Transit", "purchase", TransactionCategory.TRANSPORTATION),
    ("BART Station", "purchase", TransactionCategory.TRANSPORTATION),
    ("Amtrak", "purchase", TransactionCategory.TRANSPORTATION),
    ("Bus Ticket", "purchase", TransactionCategory.TRANSPORTATION),

    # Personal Care (6 samples)
    ("Hair Salon", "purchase", TransactionCategory.PERSONAL_CARE),
    ("Barber Shop", "purchase", TransactionCategory.PERSONAL_CARE),
    ("Spa & Massage", "purchase", TransactionCategory.PERSONAL_CARE),
    ("Nail Salon", "purchase", TransactionCategory.PERSONAL_CARE),
    ("Sephora", "purchase", TransactionCategory.PERSONAL_CARE),
    ("Dry Cleaning Service", "purchase", TransactionCategory.PERSONAL_CARE),

    # Home & Garden (6 samples)
    ("Rent Payment", "purchase", TransactionCategory.HOME),
    ("Mortgage Payment", "purchase", TransactionCategory.HOME),
    ("IKEA Furniture", "purchase", TransactionCategory.HOME),
    ("Wayfair", "purchase", TransactionCategory.HOME),
    ("Garden Nursery", "purchase", TransactionCategory.HOME),
    ("Hardware Store Tools", "purchase", TransactionCategory.HOME),

    # Education (5 samples)
    ("University Tuition", "purchase", TransactionCategory.EDUCATION),
    ("School Fee Payment", "purchase", TransactionCategory.EDUCATION),
    ("Udemy Course", "purchase", TransactionCategory.EDUCATION),
    ("Coursera", "purchase", TransactionCategory.EDUCATION),
    ("Textbook Purchase", "purchase", TransactionCategory.EDUCATION),

    # Transfer/P2P (5 samples)
    ("Venmo", "transfer", TransactionCategory.TRANSFER),
    ("Zelle Transfer", "transfer", TransactionCategory.TRANSFER),
    ("Cash App", "transfer", TransactionCategory.TRANSFER),
    ("PayPal", "transfer", TransactionCategory.TRANSFER),
    ("Bank Transfer", "transfer", TransactionCategory.TRANSFER),

    # Payment (3 samples)
    ("Credit Card Payment", "payment", TransactionCategory.PAYMENT),
    ("Bill Payment", "payment", TransactionCategory.PAYMENT),
    ("Online Payment", "payment", TransactionCategory.PAYMENT),
]


class TestCategoryAccuracy:
    """Test category accuracy with labeled dataset."""

    def test_overall_accuracy(self):
        """Test overall categorization accuracy against labeled dataset."""
        correct = 0
        total = len(LABELED_DATASET)
        mismatches = []

        for merchant_name, transaction_type, expected_category in LABELED_DATASET:
            predicted_category, confidence = infer_category(merchant_name, transaction_type)

            if predicted_category == expected_category:
                correct += 1
            else:
                mismatches.append({
                    "merchant": merchant_name,
                    "type": transaction_type,
                    "expected": expected_category.value,
                    "predicted": predicted_category.value,
                    "confidence": confidence
                })

        accuracy = (correct / total) * 100

        # Print results
        print(f"\n{'='*60}")
        print(f"CATEGORY ACCURACY TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total transactions: {total}")
        print(f"Correct predictions: {correct}")
        print(f"Incorrect predictions: {total - correct}")
        print(f"Accuracy: {accuracy:.2f}%")
        print(f"{'='*60}")

        if mismatches:
            print(f"\nMISMATCHES ({len(mismatches)}):")
            print(f"{'='*60}")
            for i, mismatch in enumerate(mismatches, 1):
                print(f"{i}. {mismatch['merchant']}")
                print(f"   Type: {mismatch['type']}")
                print(f"   Expected: {mismatch['expected']}")
                print(f"   Predicted: {mismatch['predicted']} (confidence: {mismatch['confidence']:.1f}%)")
                print()

        # Assert accuracy target
        assert accuracy >= 80.0, f"Accuracy {accuracy:.2f}% is below target of 80%"

    def test_dining_accuracy(self):
        """Test dining category accuracy."""
        dining_samples = [(m, t, c) for m, t, c in LABELED_DATASET if c == TransactionCategory.DINING]
        correct = sum(1 for m, t, c in dining_samples if infer_category(m, t)[0] == c)
        accuracy = (correct / len(dining_samples)) * 100

        print(f"\nDining Category Accuracy: {accuracy:.2f}% ({correct}/{len(dining_samples)})")
        assert accuracy >= 80.0

    def test_groceries_accuracy(self):
        """Test groceries category accuracy."""
        groceries_samples = [(m, t, c) for m, t, c in LABELED_DATASET if c == TransactionCategory.GROCERIES]
        correct = sum(1 for m, t, c in groceries_samples if infer_category(m, t)[0] == c)
        accuracy = (correct / len(groceries_samples)) * 100

        print(f"Groceries Category Accuracy: {accuracy:.2f}% ({correct}/{len(groceries_samples)})")
        assert accuracy >= 80.0

    def test_travel_accuracy(self):
        """Test travel category accuracy."""
        travel_samples = [(m, t, c) for m, t, c in LABELED_DATASET if c == TransactionCategory.TRAVEL]
        correct = sum(1 for m, t, c in travel_samples if infer_category(m, t)[0] == c)
        accuracy = (correct / len(travel_samples)) * 100

        print(f"Travel Category Accuracy: {accuracy:.2f}% ({correct}/{len(travel_samples)})")
        assert accuracy >= 80.0

    def test_shopping_accuracy(self):
        """Test shopping category accuracy."""
        shopping_samples = [(m, t, c) for m, t, c in LABELED_DATASET if c == TransactionCategory.SHOPPING]
        correct = sum(1 for m, t, c in shopping_samples if infer_category(m, t)[0] == c)
        accuracy = (correct / len(shopping_samples)) * 100

        print(f"Shopping Category Accuracy: {accuracy:.2f}% ({correct}/{len(shopping_samples)})")
        assert accuracy >= 80.0

    def test_entertainment_accuracy(self):
        """Test entertainment category accuracy."""
        entertainment_samples = [(m, t, c) for m, t, c in LABELED_DATASET if c == TransactionCategory.ENTERTAINMENT]
        correct = sum(1 for m, t, c in entertainment_samples if infer_category(m, t)[0] == c)
        accuracy = (correct / len(entertainment_samples)) * 100

        print(f"Entertainment Category Accuracy: {accuracy:.2f}% ({correct}/{len(entertainment_samples)})")
        assert accuracy >= 80.0

    def test_high_confidence_predictions(self):
        """Test that high-confidence predictions are actually accurate."""
        high_confidence_samples = []
        high_confidence_correct = 0

        for merchant_name, transaction_type, expected_category in LABELED_DATASET:
            predicted_category, confidence = infer_category(merchant_name, transaction_type)

            if confidence >= 90.0:
                high_confidence_samples.append((merchant_name, predicted_category, expected_category))
                if predicted_category == expected_category:
                    high_confidence_correct += 1

        if high_confidence_samples:
            accuracy = (high_confidence_correct / len(high_confidence_samples)) * 100
            print(f"\nHigh Confidence (≥90%) Accuracy: {accuracy:.2f}% ({high_confidence_correct}/{len(high_confidence_samples)})")

            # High confidence predictions should be highly accurate
            assert accuracy >= 95.0, f"High confidence accuracy {accuracy:.2f}% is too low"

    def test_transfer_payment_types(self):
        """Test that transfer/payment types are correctly categorized."""
        transfer_payment_samples = [
            (m, t, c) for m, t, c in LABELED_DATASET
            if c in [TransactionCategory.TRANSFER, TransactionCategory.PAYMENT]
        ]

        correct = sum(1 for m, t, c in transfer_payment_samples if infer_category(m, t)[0] == c)
        accuracy = (correct / len(transfer_payment_samples)) * 100

        print(f"Transfer/Payment Type Accuracy: {accuracy:.2f}% ({correct}/{len(transfer_payment_samples)})")
        assert accuracy == 100.0, "Transaction type-based categorization should be 100% accurate"

    def test_no_category_has_zero_accuracy(self):
        """Test that no category has 0% accuracy (complete failure)."""
        category_stats = {}

        for merchant_name, transaction_type, expected_category in LABELED_DATASET:
            if expected_category not in category_stats:
                category_stats[expected_category] = {"total": 0, "correct": 0}

            category_stats[expected_category]["total"] += 1
            predicted_category, _ = infer_category(merchant_name, transaction_type)

            if predicted_category == expected_category:
                category_stats[expected_category]["correct"] += 1

        print("\nPER-CATEGORY ACCURACY:")
        print(f"{'='*60}")

        for category, stats in sorted(category_stats.items(), key=lambda x: x[1]["correct"]/x[1]["total"], reverse=True):
            accuracy = (stats["correct"] / stats["total"]) * 100
            print(f"{category.value:20s}: {accuracy:5.1f}% ({stats['correct']}/{stats['total']})")

            # No category should have 0% accuracy
            assert accuracy > 0.0, f"Category {category.value} has 0% accuracy"