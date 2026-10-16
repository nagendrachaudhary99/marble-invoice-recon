"""Turn findings into an exceptions report and a supplier query draft."""


def exceptions_report(findings):
    by_sev = {"high": 0, "medium": 0, "low": 0}
    at_stake = 0.0
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        at_stake += f.amount_at_stake
    lines = ["# Invoice reconciliation report", ""]
    lines.append(f"Findings: {len(findings)} "
                 f"(high {by_sev['high']}, medium {by_sev['medium']}, low {by_sev['low']}); "
                 f"amount at stake ${at_stake:,.2f}")
    lines.append("")
    for f in findings:
        lines.append(f"- [{f.severity.upper()}] {f.kind} - {f.detail} "
                     f"(${f.amount_at_stake:,.2f})")
    return "\n".join(lines)


def draft_supplier_query(invoice_id, supplier, price_findings):
    items = "\n".join(f"  - {f.detail}" for f in price_findings)
    return (
        f"Subject: Invoice {invoice_id} - pricing discrepancy\n\n"
        f"Hi {supplier} team,\n\n"
        f"While reconciling invoice {invoice_id} against our contracted pricing we found:\n"
        f"{items}\n\n"
        f"Could you confirm whether these reflect a price list change we haven't "
        f"received, or a billing error? Happy to send the PO reference.\n\n"
        f"Thanks,\nAccounts"
    )
