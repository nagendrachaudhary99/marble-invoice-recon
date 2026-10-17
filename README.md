# Invoice Reconciliation Agent (restaurant back-of-house)

[![ci](https://github.com/nagendrachaudhary99/marble-invoice-recon/actions/workflows/ci.yml/badge.svg)](https://github.com/nagendrachaudhary99/marble-invoice-recon/actions/workflows/ci.yml)

Restaurants sign a purchase order with a supplier, then invoices arrive by
email and nobody checks them line by line. Marble (YC S26) is building the
autonomous back of house for restaurants and calls out exactly this in its
launch post: invoices "go unchecked while suppliers quietly raise prices line
by line." This agent does the checking: it reconciles supplier invoices
against purchase orders, flags what an operator should act on with the dollar
amount at stake and an audit trail, and drafts the supplier query email.

Built by Nagendra Chaudhary. Architecture, tradeoffs, failure handling, and
the scaling path are in [DESIGN.md](DESIGN.md). Related prior work: at AltOps
I built a multi-tenant AI agent platform automating back-office workflows
(CRMs, ERPs, email, spreadsheets); at Boys & Girls Clubs I automated
financial-document processing (Python + OCR + LLM), cutting turnaround from
3-5 days to ~30 minutes.

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
python3 -m unittest discover -s tests -v   # 12 tests
python3 -m invoicerecon.cli                # writes results/report.md + supplier query drafts
```

Verified output on the bundled demo data (4 POs, 5 invoices):

```
Findings: 6 (high 3, medium 2, low 1); amount at stake $1,887.45
- [HIGH] duplicate_invoice - INV-9004 duplicates INV-9002 ... ($639.70)
- [HIGH] duplicate_invoice - INV-9005 duplicates INV-9001 ... ($1,018.00)
- [HIGH] unit_price_creep - INV-9001: Chicken breast 40lb case billed $73.10/case vs contracted $68.00 (+7.5%) ($51.00)
- [MEDIUM] quantity_over - INV-9002: Mozzarella ... qty 6 vs ordered 5 ($54.75)
- [MEDIUM] unknown_item - INV-9003: 'Avocados 48ct' not on PO PO-1003 ($124.00)
- [LOW] missing_invoice - PO PO-1004 has no matching invoice this cycle
+ results/supplier_query_INV-9001.txt (ready-to-review email to the supplier)
```

Every finding also carries a machine-readable audit trail (`evidence` in
`results/findings.json`): the exact contracted vs billed price, quantities,
and ids that fired it.

## What is real vs mocked

- REAL: reconciliation logic, duplicate detection, tolerance handling,
  idempotent re-runs, quarantine of unparseable files, per-finding audit
  trail, exceptions report, supplier-query drafting, tests, CI.
- SYNTHETIC (hand-written, in `data/`): the purchase orders and invoices.
  No real restaurant or supplier data. The invoice JSON schema is the
  ingestion boundary - a production version parses emailed PDF scans (OCR)
  into the same schema.
- NOT INCLUDED: OCR of scanned invoices, actually sending the supplier
  email, fuzzy SKU matching - each plugs into a named boundary (loader,
  agent, Matcher interface). See DESIGN.md.

## Source

- Marble on YC: https://www.ycombinator.com/companies/joinmarble
- Launch post: https://www.ycombinator.com/launches/SAL-marble-the-autonomous-back-of-house-for-restaurants
