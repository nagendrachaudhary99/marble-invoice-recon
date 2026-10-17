# Design: invoice reconciliation agent

## Problem

Independent restaurants sign a purchase order with a supplier, then the
invoices arrive by email and nobody checks them line by line. Marble (YC S26)
calls this out in its launch post: invoices "go unchecked while suppliers
quietly raise prices line by line." A 7% bump on one chicken SKU is invisible
in a weekly stack of PDFs, and across a year it is real money. The check is
mechanical - compare every invoice line to the contracted PO - but no
operator has the hours.

## What "solved" means here

Solved: given purchase orders and invoices in the ingestion schema, every
invoice is checked for six finding types (price creep, duplicates, quantity
over, unknown item, unknown PO, missing invoice), each finding carries its
dollar amount at stake and an audit trail of the exact inputs that fired it,
output is deterministic and idempotent (re-ingesting the same file changes
nothing), unparseable files are quarantined instead of aborting the run, and
the supplier query email is drafted for the high-severity findings. The loop
"invoices in, verified exceptions + drafted supplier email out" runs end to
end.

Deliberately not solved (labeled, with the boundary named): OCR of scanned
PDF invoices (the loader is the boundary - OCR output lands in the same JSON
schema), actually sending the supplier email (the agent drafts; a human or a
mail integration sends), and fuzzy matching (renamed SKUs, unit conversions;
the Matcher interface is where it plugs in).

## Architecture

```
 supplier invoices                     purchase orders
 (emailed PDFs in prod;                 (JSON here; in prod,
  JSON files here =                     exported from the
  the ingestion boundary)               ordering system)
        |                                      |
        v                                      v
 +---------------------+              +----------------+
 | loader.py           |              | loader.py      |
 | lenient: quarantine |              |                |
 | bad files, keep     |              |                |
 | going               |              |                |
 +----------+----------+              +-------+--------+
            v                                 v
        models.py: Invoice, PurchaseOrder, LineItem
            |                                 |
            +---------------+-----------------+
                            v
              +----------------------------+
              | Matcher (Protocol)         |
              |  ExactMatcher (built)      |  FuzzyMatcher: documented next
              |   -> reconcile.py checks   |  step behind this interface
              +------------+---------------+
                           v
              dedupe_and_sort: idempotent,
              deterministic output
                           v
              +----------------------------+
              | agent.py                   |
              |  exceptions report +       |
              |  supplier query drafts     |
              +------------+---------------+
                           v
     results/report.md, findings.json (with evidence),
     supplier_query_*.txt
```

## Key tradeoffs

- **Exact matching first.** Money findings have to be explainable: "billed
  $73.10 vs contracted $68.00" is a conversation a manager can have with a
  supplier; a fuzzy score is not. Fuzzy matching (OCR noise, renamed SKUs)
  is the documented next strategy behind the `Matcher` interface, not a
  silent loosening of the checks.
- **Signature-based duplicate detection.** Duplicates are caught on supplier
  + sorted line items (sku, qty, price), not on invoice id: suppliers resend
  the same invoice with a fresh id. The inverse case (the same file ingested
  twice) is handled by idempotent ingestion keyed on invoice id, so a retry
  never produces a self-duplicate finding.
- **0.5% price tolerance.** Rounding conventions differ between suppliers;
  below tolerance is noise, above is a finding. The tolerance is a parameter
  and part of the finding's evidence.
- **Amount at stake on every finding.** A manager triages by dollars, not by
  rule names; the report sorts by severity and prints the total.
- **Deterministic output.** Findings are deduplicated and sorted so re-runs
  over the same data are byte-identical and diffable in review.

## Failure handling

- Invoice references a PO that does not exist: flagged (`unknown_po`), never
  a crash; the invoice total is reported as at stake.
- SKU on the invoice but not the PO: flagged (`unknown_item`), not silently
  skipped.
- Unparseable invoice file: quarantined, counted, and printed as a warning;
  the rest of the batch still runs.
- Same file ingested twice: no-op (idempotent ingestion by invoice id).
- Every finding carries `evidence` (contracted vs billed price, quantities,
  ids) so a wrong finding is debuggable without re-running.

## Scaling path

- **OCR ingestion.** A parser turns emailed PDF scans into the invoice JSON
  schema; parse failures land in the same quarantine path. Nothing else
  changes.
- **Volume.** Checks are independent per invoice; shard by supplier. A
  database replaces the JSON files, PO lookup becomes an index instead of a
  scan (the current `_find_po` linear scan is called out as the demo-scale
  choice).
- **FuzzyMatcher.** OCR noise and supplier-renamed SKUs need tolerance on
  identity, not just price: candidate behind the existing interface, gated
  on a labeled set before replacing ExactMatcher.
- **Closing the loop.** Supplier replies feed price-list updates; the draft
  email is the human-in-the-loop boundary today.

## Honest limits

- Demo data is synthetic and hand-written (5 invoices, 4 POs); no real
  restaurant or supplier data.
- The agent drafts the supplier email; it does not send anything.
- ExactMatcher only. A supplier renaming a SKU defeats exact matching today;
  that is the stated next milestone, not a hidden gap.
