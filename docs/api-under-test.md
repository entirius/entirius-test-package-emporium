# API endpoints under test

The backend routes the BDD suite calls, by API generation.

- Public v1: matrix (`products/`, `variants/`, `bundle-config/`, `prices-bundle/`, `options/`,
  search, `fetch_attributes=true`), contentdb (`published/{type}/`, `channels/`, `routes/`,
  `content-types/`), checkout v1 `carts/` (discount rules).
- Public v2: matrix_v2 (`products/` + `count/`, `search/`, `categories/`, `options/`, `stock/`, `omnibus/`).
- Admin v1 (JWT + IsAdminUser | ContentTypePermission): contentdb `/api-admin/contentdb/v1/`
  (`channels/`, `languages/`, `content-types/`, content DELETE guards) — auth contract only.
- Admin v2 (JWT + IsAdminUser): `/api/token/`; pim products/categories per channel
  (+ `bulk/`), features, feature-sets (+ `features/`), attributes, attributes-groups;
  suppliers mapping-profiles + validate.
- Lookup (`@lookup`, `features/lookup/lookup_check.feature`): `lookup/admin/search/`
  and `lookup/admin/check/` (JSON or multipart `image` file), reused generic v2-admin steps for
  everything except the multipart upload, the `hits`/`candidates`/`possible_duplicates`
  "contains a candidate for `<ref>`" assertion and "should not equal"
  (`features/steps/lookup_steps.py` — the lookup API's lists are never the generic `results`
  shape). BDD proves the flow runs — it does not assert a decision per pair
  class; that calibration lives in `manage.py lookup_eval` (numbers) and in the lookup module's own
  golden-pair tests (`entirius-django-lookup/tests/test_calibration_fixture_pairs.py`, mirroring
  the same fixture pairs — multipack, dirty_ean, name_only, photo_lookalike; `exact_dup`/`variant`
  already had equivalents there). Scenarios: exact EAN match (exact_dup), image-only search
  (`hits` list), image-only check of a look-alike photo never promoting to `match`
  (photo_lookalike — the image-only guard), the PIM create-hook
  (`possible_duplicates`, reuses the exact_dup pair at index 2 — see
  `scripts/seed-lookup.py` `CREATE_HOOK_PAIR_INDEX`), 401 without a token on both endpoints, and
  `@lookup-oneshot` the `duplicate_in_pim` enrichment proposal accept (`enrichment/admin/proposals/`,
  pair index 1 — `PROPOSAL_PAIR_INDEX`) — `ContentProposal.status` becomes `applied`, not
  `accepted`, on accept.
