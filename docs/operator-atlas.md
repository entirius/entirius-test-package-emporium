# Operator checklist — Atlas panel

Manual scenarios the automated suites deliberately leave to a human: gesture
flows, visual judgement, cross-panel verification. Run against a fresh
`make seed` (zeno), CMS at `http://localhost:8180` (admin / admin123).

Every row states the expected outcome — anything else is a bug (file it against
`entirius-pwa-cms` for UI behaviour, `entirius-django-atlas` for API behaviour).

## 1. Swipe review session

| # | Step | Expected |
|---|---|---|
| 1.1 | Atlas panel → Review Queue → Swipe mode | Cards for the 5 queued products (ATL-N005..N009) |
| 1.2 | Approve one card (swipe right / approve button) | Card animates away, next card shown, no error toast |
| 1.3 | Reject one card | Same — card leaves the deck |
| 1.4 | Open List mode | Approved item shows `approved`, rejected shows `rejected`; remaining stay `queued` |
| 1.5 | Card for ATL-N009 (Maple Wall Hook Set) | Stock shows 0 — visibly flagged as out of stock |

## 2. Duplicates merge

| # | Step | Expected |
|---|---|---|
| 2.1 | Atlas → Duplicates | ≥2 groups; ATL-DUP-A1/A2 suggests **merge**, ATL-DUP-B1/B2 suggests **review** (missing weight) |
| 2.2 | Merge A1 (winner) ← A2 (loser), reason "operator cleanup" | Modal requires the reason; success toast; group disappears from the list |
| 2.3 | Check the audit trail of ATL-DUP-A1 | A `manual_merge` change-log entry with the reason |
| 2.4 | Try merging across groups (A1 + B1) | Refused — EANs differ |

## 3. Auto-matched dashboard

| # | Step | Expected |
|---|---|---|
| 3.1 | Atlas → Auto-matched | ATL-ANCHOR-1 and ATL-ANCHOR-2 rows (matched via EAN from the atl-nova feed) |
| 3.2 | Expand ATL-ANCHOR-1 | Link to source atl-nova, matched_via `ean`, no violation flag |
| 3.3 | Filter "has violations" | ATL-ANCHOR-3's match attempt is NOT here (it fell back to a fresh RealProduct); list may be empty |

## 4. Updated tab + events

| # | Step | Expected |
|---|---|---|
| 4.1 | Review Queue → Updated | ATL-N004 (Birch Plant Stand) highlighted — data changed after push |
| 4.2 | Acknowledge its changes | Highlight clears; unseen counter drops |
| 4.3 | Atlas → Events | `physical_tolerance_violation` (warning) for ATL-N003 and `qms_warehouse_not_configured` (warning) for atl-push pushes |
| 4.4 | Acknowledge one warning | Row marked acknowledged, filter "unacknowledged" hides it |

## 5. Source config sanity

| # | Step | Expected |
|---|---|---|
| 5.1 | Atlas → Sources | 6 sources; KIND badges: procurement ×2, monitoring ×3, enrichment ×1 |
| 5.2 | Open atl-nova → Feeds | Feed `main` with last run `success`, 12 products imported |
| 5.3 | Trigger the feed manually (full) | Run completes; product counts unchanged (idempotent import) |
| 5.4 | Open atl-watch-pl | Untrusted flag visible; kind monitoring |
