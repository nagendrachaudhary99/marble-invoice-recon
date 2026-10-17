"""Match invoices against purchase orders and flag what a manager should see.

Checks (each produces a Finding with severity):
  unit_price_creep   invoice unit price above PO contracted price
  quantity_over      invoiced qty above ordered qty
  unknown_item       invoiced SKU not on the PO
  duplicate_invoice  same supplier + same line totals as an earlier invoice
  missing_invoice    PO with no invoice at all (reported once per run)
"""
from __future__ import annotations

from dataclasses import dataclass, field

PRICE_TOLERANCE = 0.005  # 0.5% rounding slack


@dataclass
class Finding:
    kind: str
    severity: str  # "high" | "medium" | "low"
    supplier: str
    detail: str
    amount_at_stake: float
    # audit trail: the exact inputs that fired this finding, so a manager
    # (or a reviewer of the agent's work) can verify it without re-running
    evidence: dict = field(default_factory=dict)


_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


def dedupe_and_sort(findings):
    """Deterministic, idempotent output: drop duplicate findings (same
    kind + detail, e.g. one invoice file ingested twice) and sort by
    severity, kind, then detail so re-runs over the same data produce
    identical reports."""
    seen, out = set(), []
    for f in findings:
        key = (f.kind, f.detail)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    out.sort(key=lambda f: (_SEVERITY_RANK.get(f.severity, 9), f.kind, f.detail))
    return out


def _find_po(pos, po_id):
    for po in pos:
        if po.po_id == po_id:
            return po
    return None


def reconcile(purchase_orders, invoices, price_tolerance=PRICE_TOLERANCE):
    findings = []
    seen_signatures = {}
    seen_ids = set()

    for inv in invoices:
        # idempotent ingestion: the same invoice_id processed twice (an
        # invoice emailed again, a file re-imported) is a no-op, not a
        # self-duplicate. Genuine resends carry a NEW invoice id and are
        # still caught by the signature check below.
        if inv.invoice_id in seen_ids:
            continue
        seen_ids.add(inv.invoice_id)
        po = _find_po(purchase_orders, inv.po_id)
        # duplicate detection: supplier + rounded line-item signature
        sig = (inv.supplier, tuple(sorted(
            (li.sku, round(li.qty, 3), round(li.unit_price, 4)) for li in inv.items)))
        if sig in seen_signatures:
            total = sum(li.qty * li.unit_price for li in inv.items)
            findings.append(Finding(
                "duplicate_invoice", "high", inv.supplier,
                f"{inv.invoice_id} duplicates {seen_signatures[sig]} "
                f"(same items, qty, prices)", round(total, 2),
                evidence={"invoice_id": inv.invoice_id,
                          "duplicates": seen_signatures[sig]}))
            continue
        seen_signatures[sig] = inv.invoice_id

        if po is None:
            findings.append(Finding(
                "unknown_po", "medium", inv.supplier,
                f"{inv.invoice_id} references PO {inv.po_id} which does not exist",
                round(sum(li.qty * li.unit_price for li in inv.items), 2),
                evidence={"invoice_id": inv.invoice_id, "po_id": inv.po_id}))
            continue

        po_items = {li.sku: li for li in po.items}
        for li in inv.items:
            ref = po_items.get(li.sku)
            if ref is None:
                findings.append(Finding(
                    "unknown_item", "medium", inv.supplier,
                    f"{inv.invoice_id}: '{li.name}' ({li.sku}) not on PO {po.po_id}",
                    round(li.qty * li.unit_price, 2),
                    evidence={"invoice_id": inv.invoice_id, "po_id": po.po_id,
                              "sku": li.sku}))
                continue
            if li.unit_price > ref.unit_price * (1 + price_tolerance):
                over = (li.unit_price - ref.unit_price) * li.qty
                pct = (li.unit_price / ref.unit_price - 1) * 100
                findings.append(Finding(
                    "unit_price_creep", "high", inv.supplier,
                    f"{inv.invoice_id}: {li.name} billed ${li.unit_price:.2f}/{li.unit} "
                    f"vs contracted ${ref.unit_price:.2f} (+{pct:.1f}%)",
                    round(over, 2),
                    evidence={"invoice_id": inv.invoice_id, "po_id": po.po_id,
                              "sku": li.sku, "qty": li.qty,
                              "contracted_unit_price": ref.unit_price,
                              "billed_unit_price": li.unit_price,
                              "tolerance": price_tolerance}))
            if li.qty > ref.qty:
                extra = (li.qty - ref.qty) * li.unit_price
                findings.append(Finding(
                    "quantity_over", "medium", inv.supplier,
                    f"{inv.invoice_id}: {li.name} qty {li.qty}{li.unit} "
                    f"vs ordered {ref.qty}{ref.unit}", round(extra, 2),
                    evidence={"invoice_id": inv.invoice_id, "po_id": po.po_id,
                              "sku": li.sku, "ordered_qty": ref.qty,
                              "invoiced_qty": li.qty, "unit": li.unit}))

    invoiced_pos = {inv.po_id for inv in invoices}
    for po in purchase_orders:
        if po.po_id not in invoiced_pos:
            findings.append(Finding(
                "missing_invoice", "low", po.supplier,
                f"PO {po.po_id} has no matching invoice this cycle", 0.0,
                evidence={"po_id": po.po_id}))
    return findings
