from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class LineItem:
    sku: str
    name: str
    qty: float
    unit: str
    unit_price: float


@dataclass
class PurchaseOrder:
    po_id: str
    supplier: str
    items: List[LineItem]


@dataclass
class Invoice:
    invoice_id: str
    supplier: str
    po_id: str
    date: str
    items: List[LineItem] = field(default_factory=list)
