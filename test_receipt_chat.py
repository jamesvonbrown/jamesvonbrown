#!/usr/bin/env python3
"""Unit tests for receipt_chat.py."""

import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import receipt_chat as rc

SAMPLE_RECEIPT = """13939 SE McLoughlin
H&S 3096 Oakgrove Ch
3096
Milwaukie, OR
97267
08/21/2026
11:26:56 AM

PREPAID RECEIPT

PUMP# 7

UNLEAD REG    7.849G
PRICE/GAL     $4.459
FUEL TOTAL  $ 35.00

FINAL PURCHASE
AMOUNT RECEIPT WITH
FULL TRANSACTION
DETAIL AVAILABLE
INSIDE

Customer Copy
"""


class ParseReceiptTextTests(unittest.TestCase):
    def test_parses_gas_station_receipt(self):
        parsed = rc.parse_receipt_text(SAMPLE_RECEIPT)
        self.assertEqual(parsed["date"], "2026-08-21")
        self.assertEqual(parsed["time"], "11:26:56 AM")
        self.assertEqual(parsed["category"], "Fuel")
        self.assertAlmostEqual(parsed["amount"], 35.00)
        self.assertEqual(parsed["vendor"], "13939 SE McLoughlin, H&S 3096 Oakgrove Ch, Milwaukie, OR")
        self.assertIn("7.849 gal", parsed["description"])
        self.assertIn("$4.459/gal", parsed["description"])
        self.assertIn("Pump #7", parsed["description"])

    def test_bundled_sample_file_matches(self):
        with open(rc.SAMPLE_RECEIPT_PATH) as f:
            text = f.read()
        parsed = rc.parse_receipt_text(text)
        self.assertEqual(parsed["amount"], 35.00)
        self.assertEqual(parsed["category"], "Fuel")

    def test_raises_without_total(self):
        with self.assertRaises(ValueError):
            rc.parse_receipt_text("Just some random text\nwith no total")

    def test_empty_text_raises(self):
        with self.assertRaises(ValueError):
            rc.parse_receipt_text("   \n  ")

    def test_generic_total_used_when_no_fuel_total(self):
        parsed = rc.parse_receipt_text("Corner Cafe\n01/02/2026\nTOTAL $12.50")
        self.assertEqual(parsed["amount"], 12.50)
        self.assertEqual(parsed["category"], "Dining")


class CategorizeTests(unittest.TestCase):
    def test_groceries_keyword(self):
        self.assertEqual(rc.categorize("SAFEWAY #123 GROCERY RECEIPT TOTAL $12.00"), "Groceries")

    def test_unknown_defaults_to_other(self):
        self.assertEqual(rc.categorize("Random Shop TOTAL $5.00"), "Other")


class ExpenseStoreTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)
        self.store = rc.ExpenseStore(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_add_and_persist(self):
        self.store.add(date="2026-08-21", time="", vendor="Test Vendor",
                        category="Fuel", amount=35.0, description="", raw_text="")
        reloaded = rc.ExpenseStore(self.path)
        self.assertEqual(len(reloaded.expenses), 1)
        self.assertEqual(reloaded.expenses[0].vendor, "Test Vendor")

    def test_ids_increment(self):
        e1 = self.store.add(date="2026-01-01", time="", vendor="A", category="Other",
                             amount=1, description="", raw_text="")
        e2 = self.store.add(date="2026-01-02", time="", vendor="B", category="Other",
                             amount=2, description="", raw_text="")
        self.assertEqual((e1.id, e2.id), (1, 2))

    def test_delete(self):
        e1 = self.store.add(date="2026-01-01", time="", vendor="A", category="Other",
                             amount=1, description="", raw_text="")
        self.assertTrue(self.store.delete(e1.id))
        self.assertFalse(self.store.delete(e1.id))
        self.assertEqual(len(self.store.expenses), 0)

    def test_filter_by_category_and_month(self):
        self.store.add(date="2026-08-21", time="", vendor="Gas Co", category="Fuel",
                        amount=35.0, description="", raw_text="")
        self.store.add(date="2026-07-01", time="", vendor="Gas Co", category="Fuel",
                        amount=20.0, description="", raw_text="")
        self.store.add(date="2026-08-05", time="", vendor="Cafe", category="Dining",
                        amount=10.0, description="", raw_text="")
        results = self.store.filter(category="Fuel", month="2026-08")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].amount, 35.0)

    def test_total(self):
        self.store.add(date="2026-08-21", time="", vendor="Gas Co", category="Fuel",
                        amount=35.0, description="", raw_text="")
        self.store.add(date="2026-08-05", time="", vendor="Cafe", category="Dining",
                        amount=10.0, description="", raw_text="")
        self.assertAlmostEqual(self.store.total(), 45.0)
        self.assertAlmostEqual(self.store.total(category="Fuel"), 35.0)


class CommandHandlingTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)
        self.store = rc.ExpenseStore(self.path)
        self.store.add(date="2026-08-21", time="11:26:56 AM", vendor="Gas Station",
                        category="Fuel", amount=35.0, description="7.849 gal", raw_text="")
        self.store.add(date="2026-08-05", time="", vendor="Cafe", category="Dining",
                        amount=10.0, description="", raw_text="")

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_handle_list_no_filter(self):
        output = rc.handle_list(self.store, "list")
        self.assertIn("Gas Station", output)
        self.assertIn("Cafe", output)

    def test_handle_list_with_category_filter(self):
        output = rc.handle_list(self.store, "list category:Fuel")
        self.assertIn("Gas Station", output)
        self.assertNotIn("Cafe", output)

    def test_handle_list_empty_result(self):
        output = rc.handle_list(self.store, "list category:Pharmacy")
        self.assertEqual(output, "No expenses found.")

    def test_handle_total(self):
        output = rc.handle_total(self.store, "total")
        self.assertIn("45.00", output)

    def test_handle_delete_missing_id(self):
        output = rc.handle_delete(self.store, "delete 999")
        self.assertIn("No expense", output)

    def test_handle_delete_usage(self):
        output = rc.handle_delete(self.store, "delete")
        self.assertIn("Usage", output)

    def test_handle_delete_success(self):
        output = rc.handle_delete(self.store, "delete 1")
        self.assertIn("Deleted expense #1", output)
        self.assertEqual(len(self.store.expenses), 1)

    @patch("receipt_chat.datetime")
    def test_freeform_query_category_and_month(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2026, 8, 25)
        output = rc.handle_freeform(self.store, "how much did I spend on fuel this month")
        self.assertIn("35.00", output)

    def test_freeform_unrecognized(self):
        output = rc.handle_freeform(self.store, "what's the weather like")
        self.assertIn("didn't understand", output)


if __name__ == "__main__":
    unittest.main()
