"""Load purchase orders (JSON) and invoices (one JSON file each)."""
import json
import os

from .models import Invoice, LineItem, PurchaseOrder


def _line(d):
    return LineItem(sku=d["sku"], name=d["name"], qty=float(d["qty"]),
                    unit=d["unit"], unit_price=float(d["unit_price"]))


def load_purchase_orders(path):
    with open(path) as f:
        data = json.load(f)
    return [PurchaseOrder(po_id=p["po_id"], supplier=p["supplier"],
                          items=[_line(i) for i in p["items"]]) for p in data]


def load_invoices(directory):
    invoices = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(directory, name)) as f:
            d = json.load(f)
        invoices.append(Invoice(invoice_id=d["invoice_id"], supplier=d["supplier"],
                                po_id=d["po_id"], date=d["date"],
                                items=[_line(i) for i in d["items"]]))
    return invoices
