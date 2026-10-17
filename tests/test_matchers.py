import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from invoicerecon.loader import load_invoices, load_invoices_verbose, load_purchase_orders
from invoicerecon.matchers import ExactMatcher, Matcher
from invoicerecon.reconcile import dedupe_and_sort, reconcile

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


class TestMatchers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pos = load_purchase_orders(os.path.join(DATA, "purchase_orders.json"))
        cls.invoices = load_invoices(os.path.join(DATA, "invoices"))

    def test_exact_matcher_satisfies_interface(self):
        self.assertIsInstance(ExactMatcher(), Matcher)

    def test_matcher_output_is_deduped_sorted_and_deterministic(self):
        m = ExactMatcher()
        first = m.match(self.pos, self.invoices)
        second = m.match(self.pos, self.invoices)
        self.assertEqual([(f.kind, f.detail) for f in first],
                         [(f.kind, f.detail) for f in second])
        self.assertEqual(len(first), 6)  # demo data expectation, unchanged
        ranks = {"high": 0, "medium": 1, "low": 2}
        sevs = [ranks[f.severity] for f in first]
        self.assertEqual(sevs, sorted(sevs))

    def test_double_ingest_is_idempotent(self):
        m = ExactMatcher()
        once = m.match(self.pos, self.invoices)
        twice = m.match(self.pos, self.invoices + self.invoices)
        self.assertEqual([(f.kind, f.detail) for f in once],
                         [(f.kind, f.detail) for f in twice])

    def test_findings_carry_audit_evidence(self):
        for f in dedupe_and_sort(reconcile(self.pos, self.invoices)):
            self.assertTrue(f.evidence, f"finding without evidence: {f}")
        creep = [f for f in reconcile(self.pos, self.invoices)
                 if f.kind == "unit_price_creep"][0]
        self.assertEqual(creep.evidence["contracted_unit_price"], 68.00)
        self.assertEqual(creep.evidence["billed_unit_price"], 73.10)

    def test_unparseable_invoice_is_quarantined_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "bad.json"), "w") as f:
                f.write("{not json")
            with open(os.path.join(d, "missing_keys.json"), "w") as f:
                json.dump({"invoice_id": "X"}, f)
            invoices, quarantined = load_invoices_verbose(d)
        self.assertEqual(invoices, [])
        self.assertEqual(len(quarantined), 2)


if __name__ == "__main__":
    unittest.main()
