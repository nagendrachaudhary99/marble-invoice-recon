# Invoice reconciliation report

Findings: 6 (high 3, medium 2, low 1); amount at stake $1,887.45

- [HIGH] unit_price_creep - INV-9001: Chicken breast 40lb case billed $73.10/case vs contracted $68.00 (+7.5%) ($51.00)
- [MEDIUM] quantity_over - INV-9002: Mozzarella shredded 20lb qty 6.0case vs ordered 5.0case ($54.75)
- [MEDIUM] unknown_item - INV-9003: 'Avocados 48ct' (AVC-HAS-48) not on PO PO-1003 ($124.00)
- [HIGH] duplicate_invoice - INV-9004 duplicates INV-9002 (same items, qty, prices) ($639.70)
- [HIGH] duplicate_invoice - INV-9005 duplicates INV-9001 (same items, qty, prices) ($1,018.00)
- [LOW] missing_invoice - PO PO-1004 has no matching invoice this cycle ($0.00)
