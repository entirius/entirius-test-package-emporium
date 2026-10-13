# Tags

Which tag selects what (`make bdd TAGS=@tag`), and which tags need more than a seeded backend.

## Tag taxonomy

| Tag | Scope |
|-----|-------|
| `@import-verification` | Tests verifying the CSV import pipeline |
| `@matrix`, `@matrix-v2` | Matrix read model (public product API) |
| `@pim-csv` | CSV-to-API data comparison |
| `@pricemanager` | Price verification |
| `@qms` | Quantity/stock verification |
| `@contentdb` | ContentDB published content, routes |
| `@checkout`, `@discount-rules` | Cart and discount rules |
| `@admin`, `@pim-admin`, `@v2`, `@crud` | Authenticated admin API tests |
| `@suppliers` | Supplier feeds, mapping, delta sync |
| `@access` | Access gate: roles, refusals, grants, audit, staff accounts, application tokens, legacy keys per channel, pinned erase (re-runnable) |
| `@spec-first` | Scenarios written ahead of step implementation — excluded from `make test`/`make bdd` |

## Tags with preconditions

- `@access` (`features/access/`, plus the scenarios of `@access-security`; needs `django_access` and its seeded
  role users `viewer`/`editor`/`manager`, `scripts/seed-access.py`): roles, gate refusals, 404 stays 404, SKU delete,
  custom role + grant, audit (`gate.bypass` for superuser writes only), staff accounts created through the admin API
  (sign-in through `customer/tokens/`, refusals), application tokens (scope, channel pin, revoke, rotate) and the
  legacy checkout key — one pinned token per seed channel. Re-runnable on one database: run-unique names, every
  created object deleted, revoked or deactivated at the scenario's end (applications cannot be deleted — they stay,
  inactive; created staff accounts stay too, there is no delete endpoint).
- `@access-security` (`features/access/security/`, also tagged `@access`; needs the seeded role users
  plus `accessadmin`/`norole`): principal × route class × method matrix (incl. Django admin, superusers only, over a session),
  public/customer/key routes unchanged for shoppers, token abuse — one answer for every failure kind, legacy
  key expiry, `access.manage` built-in only, mass assignment, secret tokens without a lifetime cap,
  sensitive routes, a pinned erase token erases only in its channel, superuser `gate.bypass` audit,
  secret hygiene. Re-runnable on one database. Service/worker logs and the Redis key list of a run can be checked
  with `scripts/secret_scan.py --fixtures fixtures` (`docs/harness.md`).
- `@harness` (`features/harness/mail_roundtrip.feature`): harness plumbing only — no module,
  no API; needs GreenMail (in the entirius-zeno harness: `make mail`).
- `@needs-toolbox` (scenario level; the outage feature as a whole): the scenario needs a live AI completion — an AI
  template draft, a lead analysis, or a later step of a chain built on one. `before_scenario` skips it with the
  reason unless the public munin registry reports `platform.toolbox.state` = `configured`
  (`entirius_tests.munin.parse_toolbox_state`; an older munin is read through `platform.toolbox_status`). A failed
  probe skips nothing. Scenarios that only prove a refusal or use a static template carry no tag.
- Module tags gated by the munin registry (`MODULE_TAGS`): `atlas`, `pricefighter`, `suppliers`, `leads`,
  `communicator`, `siteintel`, `notifications` — a feature carrying one is skipped when the backend lacks it, on top
  of the modules of its directory (`docs/harness.md` § Module subsets).

One-shot tags (`@lookup-oneshot`, `@leads-oneshot`, `@communicator-oneshot`, `@toolbox-oneshot`): see
`docs/harness.md` § One-shot scenarios.
