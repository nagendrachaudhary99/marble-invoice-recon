import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from invoicerecon.loader import load_invoices, load_purchase_orders
from invoicerecon.models import Invoice, LineItem, PurchaseOrder
from invoicerecon.reconcile import reconcile

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


class TestReconcile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pos = load_purchase_orders(os.path.join(DATA, "purchase_orders.json"))
        cls.invoices = load_invoices(os.path.join(DATA, "invoices"))
        cls.findings = reconcile(cls.pos, cls.invoices)
        cls.by_kind = {}
        for f in cls.findings:
            cls.by_kind.setdefault(f.kind, []).append(f)

    def test_price_creep_flagged_with_amount(self):
        creep = self.by_kind.get("unit_price_creep", [])
        self.assertEqual(len(creep), 1)  # INV-9005 is dup of 9001, skipped
        self.assertIn("INV-9001", creep[0].detail)
        self.assertAlmostEqual(creep[0].amount_at_stake, (73.10 - 68.00) * 10, places=2)

    def test_quantity_over_flagged(self):
        q = self.by_kind.get("quantity_over", [])
        self.assertEqual(len(q), 1)
        self.assertIn("Mozzarella", q[0].detail)

    def test_unknown_item_flagged(self):
        u = self.by_kind.get("unknown_item", [])
        self.assertEqual(len(u), 1)
        self.assertIn("Avocados", u[0].detail)

    def test_duplicate_invoice_flagged(self):
        d = self.by_kind.get("duplicate_invoice", [])
        self.assertEqual(len(d), 2)  # INV-9004 dups INV-9002; INV-9005 dups INV-9001
        details = " ".join(x.detail for x in d)
        self.assertIn("INV-9004", details)
        self.assertIn("INV-9005", details)

    def test_missing_invoice_flagged(self):
        m = self.by_kind.get("missing_invoice", [])
        self.assertEqual(len(m), 1)
        self.assertIn("PO-1004", m[0].detail)

    def test_clean_invoice_passes(self):
        # INV-9003 has one unknown item but no price/qty flags on known items
        for f in self.findings:
            if "INV-9003" in f.detail:
                self.assertEqual(f.kind, "unknown_item")

    def test_tolerance_allows_tiny_rounding(self):
        pos = [PurchaseOrder("P1", "S", [LineItem("A", "x", 1, "ea", 10.00)])]
        invs = [Invoice("I1", "S", "P1", "2026-01-01",
                        [LineItem("A", "x", 1, "ea", 10.04)])]  # within 0.5%
        self.assertEqual(reconcile(pos, invs), [])


if __name__ == "__main__":
    unittest.main()
