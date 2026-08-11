# Operator checklist — PriceFighter panel

Manual scenarios for the pricing operator. Run against a fresh `make seed`
(zeno), CMS at `http://localhost:8180` (admin / admin123). The decision list is
computed live — numbers below come from the seeded calibration on the
default-europe / DE / EUR market (tax 19%, baseline = cost × 1.20 × 1.19).

## 1. Reading the gap analysis

| # | Step | Expected |
|---|---|---|
| 1.1 | PriceFighter panel → decisions list | Rows sorted by gap; recommendation chips: compete, raise, hold, hold_at_floor, no_recommendation |
| 1.2 | ENT-C002 row | compete — current 319.00, competitor 289.00, suggested **287.00** |
| 1.3 | ENT-D001 row | raise — competitor at 1100.00, suggested **1098.00** (desks category rule) |
| 1.4 | ENT-O001 row | hold_at_floor — price war active, floor **262.40** (margin floor beats MAP 259) |
| 1.5 | ENT-B001 row | no_recommendation — reason `no_cost` (no purchase cost on file) |
| 1.6 | Filter recommendation = compete | Only compete rows remain; ENT-C001 appears on several markets (global watcher) |

## 2. Observation flags in the detail

The detail shows the latest observation **per source**, and sources scoped to a
different country are dropped from that market entirely — flags are spread
across markets by design.

| # | Step | Expected |
|---|---|---|
| 2.1 | Open ENT-S001 detail (DE market) | Two rows: DE watcher flagged **out-of-stock** (its newer 879.00/stock-0 hides the earlier 899.00) and the global watcher flagged **currency mismatch** (PLN on a EUR market) |
| 2.2 | Open ENT-S001 detail (PL market) | The PL watcher's row appears here, flagged **untrusted** |
| 2.3 | Open ENT-S002 detail | Its only observation is flagged **stale** (10 days old) and the sku is absent from the default list |

## 3. Applying a decision

| # | Step | Expected |
|---|---|---|
| 3.1 | Apply ENT-C002 at the suggested 287.00 | Success — bucket `applied` |
| 3.2 | Check History | New entry for ENT-C002, strategy compete, old 319.00 → new 287.00 |
| 3.3 | Cross-check in the Pricing panel | ENT-C002 current price is 287.00, source `pricefighter` |
| 3.4 | Re-open decisions | ENT-C002 still shows `compete`, but suggested price equals the current 287.00 — a re-apply is a no-op (the gap anchors on baseline, not on your price) |
| 3.5 | Apply ENT-C001 on the **FR** market | Refused — bucket `skipped` (price owned by `admin_edit`) |

## 4. Stale-price protection

| # | Step | Expected |
|---|---|---|
| 4.1 | Open a compete row, note the suggested price | — |
| 4.2 | In another tab, change that price in the Pricing panel | — |
| 4.3 | Apply the noted (now outdated) suggestion | Refused — bucket `stale`, nothing written |

## 5. History review

| # | Step | Expected |
|---|---|---|
| 5.1 | History tab after fresh seed | ≥3 entries: ENT-C003 compete apply, ENT-X001 apply at MAP floor, ENT-X001 **revert_baseline clamped** to MAP 1900.00 |
| 5.2 | Open the revert entry | Reason snapshot shows baseline 1856.40 and the clamp to 1900.00 |
