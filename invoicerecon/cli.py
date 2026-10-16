#!/usr/bin/env python3
"""Run reconciliation over the demo data and write the report.

Usage: python3 -m invoicerecon.cli [--data DIR]
"""
import argparse
import json
import os

from .agent import draft_supplier_query, exceptions_report
from .loader import load_invoices, load_purchase_orders
from .reconcile import reconcile


def main():
    here = os.path.dirname(__file__)
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(here, "..", "data"))
    ap.add_argument("--out", default=os.path.join(here, "..", "results"))
    args = ap.parse_args()

    pos = load_purchase_orders(os.path.join(args.data, "purchase_orders.json"))
    invoices = load_invoices(os.path.join(args.data, "invoices"))
    findings = reconcile(pos, invoices)

    report = exceptions_report(findings)
    print(report)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "report.md"), "w") as f:
        f.write(report + "\n")
    with open(os.path.join(args.out, "findings.json"), "w") as f:
        json.dump([vars(x) for x in findings], f, indent=2)

    # draft supplier queries for high-severity price creep, grouped by invoice
    by_inv = {}
    for x in findings:
        if x.kind == "unit_price_creep":
            inv_id = x.detail.split(":")[0]
            by_inv.setdefault((x.supplier, inv_id), []).append(x)
    for (supplier, inv_id), fs in by_inv.items():
        draft = draft_supplier_query(inv_id, supplier, fs)
        fname = os.path.join(args.out, f"supplier_query_{inv_id}.txt")
        with open(fname, "w") as f:
            f.write(draft + "\n")
        print(f"\nwrote {fname}")


if __name__ == "__main__":
    main()
