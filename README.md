# Invoice Reconciliation Agent (restaurant back-of-house)

A small working slice of the problem Marble (YC S26) describes in its Founding
Engineer posting: restaurant invoices "go unchecked while suppliers quietly
raise prices line by line." This agent reconciles supplier invoices against
purchase orders and flags what an operator should act on — then drafts the
supplier query email.

Built by Nagendra Chaudhary. Related prior work: at AltOps I built a
multi-tenant AI agent platform automating back-office workflows (CRMs, ERPs,
email, spreadsheets) with deterministic reconciliation of agent runs; at Boys
& Girls Clubs I automated financial-document processing (Python + OCR + LLM)
that cut turnaround from 3–5 days to ~30 minutes.

## Checks

| finding            | severity | meaning                                             |
|--------------------|----------|-----------------------------------------------------|
| unit_price_creep   | high     | billed unit price above contracted PO price (>0.5%) |
| duplicate_invoice  | high     | same supplier + identical items/qty/prices twice    |
| quantity_over      | medium   | invoiced qty above ordered qty                      |
| unknown_item       | medium   | SKU on invoice but not on the PO                    |
| unknown_po         | medium   | invoice references a PO that does not exist         |
| missing_invoice    | low      | PO with no invoice this cycle                       |

## Run it

```sh
python3 -m unittest discover -s tests -v   # 7 tests
python3 -m invoicerecon.cli                # writes results/report.md + supplier query drafts
```

Verified output on the bundled demo data (4 POs, 5 invoices):

```
Findings: 6 (high 3, medium 2, low 1); amount at stake $1,887.45
- [HIGH] unit_price_creep - INV-9001: Chicken breast 40lb case billed $73.10/case vs contracted $68.00 (+7.5%) ($51.00)
- [HIGH] duplicate_invoice - INV-9004 duplicates INV-9002 ... ($639.70)
- [HIGH] duplicate_invoice - INV-9005 duplicates INV-9001 ... ($1,018.00)
- [MEDIUM] quantity_over - INV-9002: Mozzarella ... qty 6 vs ordered 5 ($54.75)
- [MEDIUM] unknown_item - INV-9003: 'Avocados 48ct' not on PO PO-1003 ($124.00)
- [LOW] missing_invoice - PO PO-1004 has no matching invoice this cycle
+ results/supplier_query_INV-9001.txt (ready-to-review email to the supplier)
```

## What is real vs mocked

- REAL: reconciliation logic, duplicate detection, tolerance handling,
  exceptions report, supplier-query drafting, tests.
- SYNTHETIC (hand-written, in `data/`): the purchase orders and invoices.
  No real restaurant or supplier data. The invoice JSON schema is the
  ingestion boundary — a production version would parse emailed PDF scans
  (OCR) into the same schema.
- NOT INCLUDED: OCR of scanned invoices, supplier email sending, demand
  forecasting — those plug into the same boundaries (loader for OCR output,
  agent for sending).

## Source

- Marble on YC: https://www.ycombinator.com/companies/joinmarble
- Launch post: https://www.ycombinator.com/launches/SAL-marble-the-autonomous-back-of-house-for-restaurants
