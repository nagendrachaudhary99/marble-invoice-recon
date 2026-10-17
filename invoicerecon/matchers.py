"""Matching strategies: how invoices get reconciled against purchase orders.

Matcher is the interface. ExactMatcher is the built strategy: exact PO
references and SKUs, signature-based duplicate detection, 0.5% price
tolerance. A fuzzy matcher (OCR noise, renamed SKUs, unit conversions)
plugs in behind the same interface. See DESIGN.md.
"""
from typing import Protocol, runtime_checkable

from .reconcile import dedupe_and_sort, reconcile


@runtime_checkable
class Matcher(Protocol):
    name: str

    def match(self, purchase_orders, invoices):
        """Return the deduplicated, deterministically sorted findings."""
        ...


class ExactMatcher:
    name = "exact"

    def match(self, purchase_orders, invoices):
        return dedupe_and_sort(reconcile(purchase_orders, invoices))
