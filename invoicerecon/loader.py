"""Load purchase orders (JSON) and invoices (one JSON file each).

Invoice loading is lenient by design: an unparseable file is quarantined
(skipped and counted) instead of aborting the whole reconciliation run,
and the quarantine count is surfaced by the CLI. See DESIGN.md."""
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


def load_invoices_verbose(directory):
    """Return (invoices, quarantined_filenames). A file that fails to parse
    or is missing required keys is quarantined, not fatal."""
    invoices, quarantined = [], []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, name)) as f:
                d = json.load(f)
            invoices.append(Invoice(
                invoice_id=d["invoice_id"], supplier=d["supplier"],
                po_id=d["po_id"], date=d["date"],
                items=[_line(i) for i in d["items"]]))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            quarantined.append(name)
    return invoices, quarantined


def load_invoices(directory):
    return load_invoices_verbose(directory)[0]
