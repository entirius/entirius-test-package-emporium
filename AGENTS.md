# AGENTS.md

BDD test suite + demo data package (Emporium) for the Entirius/Volkanos platform —
repo `entirius-test-package-emporium`, import `entirius_tests`.
Tests both public API (CSV-imported data verification) and authenticated admin API (CRUD).
Runs as an external consumer against a running Volkanos backend seeded with `package/`.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | behave dry-run — steps bind to scenarios, no API needed — plus the pytest unit tests in `tests/` |
| `make unit` | only the pytest unit tests for the assertion step definitions, no API needed |
| `make bdd [TAGS=@tag]` | full BDD suite against a live API (`API_BASE_URL`); a single tag reads only the feature files carrying it, so the summary's skipped count holds real skips only (tag expressions keep the whole tree) |
| `make e2e [E2E_ARGS=…] [E2E_DEVICE=…]` | Playwright e2e; `E2E_ARGS` narrows pytest targets (default `e2e/`), `E2E_DEVICE` emulates a Playwright device (`e2e/conftest.py`) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + behave; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the import package `entirius_tests` — it is a public API contract.
- Default: do not commit — git is the user's call.
- **Data-driven**: `csv_loader.py` parses the actual CSV files; zero hardcoded expected values
  in public API features. If test data changes, tests verify the new data automatically.
- **Config-driven channels**: no channel names in `.feature` files.
- **BDD-prefixed test data**: all test-created resources use `bdd-` / `BDD-` prefix
  to avoid collision with imported data; CRUD scenarios start with idempotent cleanup
  (`Given I ensure v2 admin resource ... is deleted`).
- **Auth lifecycle**: `context.api.clear_auth_token()` in `before_scenario`;
  re-authenticate per scenario via a Background step.
- **context.saved**: per-scenario dict for inter-step state; URL paths resolve
  `{channel_idx}` and `{saved.alias}` placeholders automatically — the alias name itself carries
  the `saved.` prefix (`I save the response field "id" as "saved.proposal_id"`, then
  `{saved.proposal_id}` in a later path), it is not special templating syntax.
- **One-shot scenarios** (`@lookup-oneshot`, `@leads-oneshot` — incl. the `@funnel` feature —,
  `@communicator-oneshot` and `@toolbox-oneshot` (`@toolbox-down`, simulated toolbox outage) here; also suppliers audit-trail, atlas push/merge):
  mutate a specific pre-seeded row once per database — re-running them against an already-consumed
  DB fails on purpose. A BDD re-run needs a fresh `make seed` (zeno `AGENTS.md` §Green baselines).

## Architecture

```
├── src/entirius_tests/     # Shared library (pip install -e .)
│   ├── api_client.py       # HTTP client (GET/POST/PATCH/DELETE + JWT auth)
│   ├── auth.py             # JWT token acquisition
│   ├── csv_loader.py       # Parse CSV from package/
│   ├── assertions.py       # Assert helpers + extract_items()
│   ├── mail.py             # GreenMail sandbox: purge/count/read (REST), send (SMTP), inject (IMAP APPEND)
│   └── clock.py            # communicator dev-only test endpoints: channel clock, send-due, poll-now
├── features/               # Behave BDD features
│   ├── environment.py      # before_all: API client + channels; before_scenario: reset + clear auth
│   ├── steps/              # Shared step definitions (HTTP verbs, assertions, admin CRUD, domains)
│   ├── admin/  suppliers/  matrix/  matrix_v2/  pim_csv/  checkout/  lookup/
│   └── contentdb/  pricemanager/  qms/  faq/  deliverypoints/  agreements/  contact_forms/
├── package/                # Emporium demo dataset (CSV; see package/README.md)
├── fixtures/               # Django YAML fixtures (loaddata)
│   ├── mail/               # hand-written .eml: replies, autoresponder, opt-outs, DSN hard/soft, duplicate
│   ├── siteintel/          # anonymised PSI/URLScan recordings (psi/, urlscan/) + synthetic sites/{good,slow,broken}
│   └── lookup/             # Calibration set (dev-plan 09): pim_products.json, atlas_products.json,
│                           # labelled_pairs.csv, img/*.png — see scripts/generate-lookup-fixtures.py
├── images/                 # Product images per SKU
├── devtools/               # Bulk data multiplier (stress tests)
├── scripts/                # Seed (host) + import (container) + behave.ini generator
│   ├── anonymise-siteintel-recordings.py  # private export -> fixtures/siteintel (mapping to stdout only);
│   │                                      # --verify fixtures/siteintel = leak gate only (.gitleaks.toml words, hosts, emails, IPs)
│   ├── generate-lookup-fixtures.py  # deterministic (fixed seed) — regenerate + commit, not run at seed time
│   ├── seed-access.py               # seed.sh Step 3e — role staff users (README § Key settings); Step 4b imports legacy keys
│   ├── secret_scan.py               # stdin → counts of ent_api_ tokens + legacy fixture keys (never a match); exit 1 on any
│   └── seed-lookup.py               # seed.sh Step 6z — loads fixtures/lookup/, backfills, seeds one proposal
├── tests/                  # pytest for scripts/ (`uv run --extra e2e pytest tests/`)
├── e2e/                    # Playwright E2E (cms/, storefront/; conftest.py = E2E_DEVICE emulation)
│                           # leads funnel (page objects, determinism, zeno commands): docs/e2e-leads-funnel.md
└── load/                   # Load tests k6 (planned)
```

## Configuration

`behave.ini` is gitignored — copy `behave.ini.example` or generate via
`scripts/generate-behave-ini.sh`. Priority: env vars > `behave.ini` `[behave.userdata]` >
auto-discovery (`discover_channels()` scans `products--{channel}.csv` filenames).
Key settings table: see `README.md`.

## Step patterns (essentials)

- Public (CSV-driven): `the channel is the primary channel`, `the response count should be at
  least the CSV product count`, `the CSV attributes should be non-empty`.
- ContentDB: `I GET the ContentDB published endpoint "{path}"` (+ `with channel` / `with routes`).
- ContentDB admin v1 (JWT, `/api-admin/` prefix — not the v2 `/api/` shape):
  `I GET/DELETE the ContentDB admin endpoint "{path}" [without auth]`.
- Admin v2 (JWT): `Given I am authenticated as an admin/regular user`;
  `When I GET/POST/PATCH/DELETE the v2 admin endpoint "{path}" [with body|with params|without auth]`.
- Assertions: `the response field "{field}" should equal/be true/be null/be a dict…`,
  `the results should contain an item with "{key}" equal to "{value}"`,
  `I save the response field "{field}" as "{alias}"`.
- Mail sandbox (`features/steps/mail.py`): `the sandbox mailbox is empty` (purges), `the sandbox mailbox
  contains {n} messages`, `I inject the fixture mail "{name}" into INBOX [replying to "{saved.alias}"]`,
  `I send the fixture mail "{name}" over SMTP to the sandbox`, `the last sandbox message has header "{h}"
  equal to "{v}"` (resolves `{saved.alias}`), `the last sandbox message subject starts with "{prefix}"`,
  `the value "{value}" is saved as "{alias}"`. Fixture mails use a `{message_id}` placeholder (single braces)
  in `In-Reply-To`/`References`/`Original-Message-ID`; `duplicate.eml` shares `Message-ID` with `reply_plain.eml`.
- Access (`features/steps/access_steps.py`, shared with the security matrix): `I am authenticated as the
  {viewer|editor|manager} staff user`, `the gate refuses with issue "{ACCESS_DENIED|STAFF_ONLY|UNMAPPED_ROUTE}"`,
  `the refusal names "{text}"`, `the response is not a gate refusal`, `the permission "{area}" should be
  "{level}"|absent` (on `access/me/`), audit lookups after `I save the newest audit entry id as "{alias}"`,
  `an application "{alias}" for this run` + `a token "{alias}" of application … with scope "{scope}" [pinned to the
  first|second seed channel]`, `I submit a contact form with the token "{alias}" on the first|second seed channel`.
  Raw token values stay in `context.raw_tokens` — never printed, never in `context.saved` or an assertion message.
  `the admin sends {METHOD} to "{path}" when the scenario ends` registers a cleanup that runs even when the
  scenario fails (resolved at the end; an alias never saved means nothing to clean).
- Access security (`@access-security`, same file): `the caller is {anonymous|customer|bad-bearer|token-only|norole|
  viewer|editor|manager|accessadmin|admin}` (a requests session with exactly those headers; token-only = fresh
  publishable + secret tokens, no JWT), `the caller has a Django admin session as {who}`, `the caller presents the
  {-|checkout fixture|contact-forms fixture|<scope>} key`, `the caller sends {METHOD} to "{path}"` (POST = `{}`;
  `with JSON <cell>` / `with body` docstring; `{days_ahead:N}` → an ISO instant), `the answer is {status} with
  "{gate issue|-|n/a|login redirect}"` (`-` = no gate issue, `n/a` = HEAD). Token abuse: `the tokens "a, b" are sent in
  "{header}" with {METHOD} to "{path}"` → `every answer is the same {status}`, `no answer carries a token secret`.
  Tokens of these steps live in the shared, never-deactivated application `bdd-access-security` (revoked per
  scenario, 30-day expiry); a `raw` in any answer moves to `context.raw_tokens` and its token is revoked at the end.
  Audit: `the audit log counts {n} "gate.bypass" after "{mark}" for {METHOD} "{route}" [with status {s}]`.
- Clock (`features/steps/clock.py`, needs the channel + admin auth): `the channel clock is {weekday} {time}`,
  `the beat send task has run`, `the IMAP poll task has run`.
- `seed.sh` purges GreenMail once when `GREENMAIL_API_URL` is set (zeno passes it; a warning otherwise).
  Scenarios needing an empty mailbox purge in their own `Background` — never rely on order.

## Tags

- `@access` (`features/access/`, 21 scenarios + the 486 of `@access-security`; needs `django_access` and its seeded
  role users `viewer`/`editor`/`manager`, `scripts/seed-access.py`): roles, gate refusals, 404 stays 404, SKU delete,
  custom role + grant, audit (`gate.bypass` for superuser writes only), application tokens (scope, channel pin,
  revoke, rotate) and the legacy checkout key. Re-runnable on one database: run-unique names, every created object
  deleted, revoked or deactivated at the scenario's end (applications cannot be deleted — they stay, inactive).
- `@access-security` (`features/access/security/`, 486 scenarios, also tagged `@access`; needs the seeded role users
  plus `accessadmin`/`norole`): principal × route class × method matrix (366 rows, incl. Django admin over a session),
  public/customer/key routes unchanged for shoppers (69), token abuse — one answer for every failure kind, legacy
  key expiry (11), `access.manage` built-in only, mass assignment, secret-token expiry ≤ 365 days (32), superuser
  `gate.bypass` audit (3), secret hygiene (5). Re-runnable on one database. The zeno gate pipes service/worker logs and
  the Redis key list through `scripts/secret_scan.py --fixtures fixtures`.
- `@harness` (`features/harness/mail_roundtrip.feature`, 2 scenarios): harness plumbing only — no module,
  no API; needs GreenMail (zeno `make mail`).
- Module tags gated by the munin registry (`MODULE_TAGS`): `atlas`, `pricefighter`, `suppliers`, `leads`,
  `communicator`, `siteintel`, `notifications` — a feature carrying one is skipped when the backend lacks it.

## API endpoints under test

- Public v1: matrix (`products/`, `variants/`, `bundle-config/`, `prices-bundle/`, `options/`,
  search, `fetch_attributes=true`), contentdb (`published/{type}/`, `channels/`, `routes/`,
  `content-types/`), checkout v1 `carts/` (discount rules).
- Public v2: matrix_v2 (`products/` + `count/`, `search/`, `categories/`, `options/`, `stock/`, `omnibus/`).
- Admin v1 (JWT + IsAdminUser | ContentTypePermission): contentdb `/api-admin/contentdb/v1/`
  (`channels/`, `languages/`, `content-types/`, content DELETE guards) — auth contract only.
- Admin v2 (JWT + IsAdminUser): `/api/token/`; pim products/categories per channel
  (+ `bulk/`), features, feature-sets (+ `features/`), attributes, attributes-groups;
  suppliers mapping-profiles + validate.
- Lookup (`@lookup`, `features/lookup/lookup_check.feature`, 7 scenarios): `lookup/admin/search/`
  and `lookup/admin/check/` (JSON or multipart `image` file), reused generic v2-admin steps for
  everything except the multipart upload, the `hits`/`candidates`/`possible_duplicates`
  "contains a candidate for `<ref>`" assertion and "should not equal"
  (`features/steps/lookup_steps.py` — the lookup API's lists are never the generic `results`
  shape). BDD proves the flow runs (test-strategy.md §5) — it does not assert a decision per pair
  class; that calibration lives in `manage.py lookup_eval` (numbers) and in the lookup module's own
  golden-pair tests (`entirius-django-lookup/tests/test_calibration_fixture_pairs.py`, mirroring
  the same fixture pairs — multipack, dirty_ean, name_only, photo_lookalike; `exact_dup`/`variant`
  already had equivalents there). Scenarios: exact EAN match (exact_dup), image-only search
  (`hits` list), image-only check of a look-alike photo never promoting to `match`
  (photo_lookalike — the image-only guard, research r01 §2/§3), the PIM create-hook
  (`possible_duplicates`, plan 07, reuses the exact_dup pair at index 2 — see
  `scripts/seed-lookup.py` `CREATE_HOOK_PAIR_INDEX`), 401 without a token on both endpoints, and
  `@lookup-oneshot` the `duplicate_in_pim` enrichment proposal accept (`enrichment/admin/proposals/`,
  plan 06, pair index 1 — `PROPOSAL_PAIR_INDEX`) — `ContentProposal.status` becomes `applied`, not
  `accepted`, on accept.

## Writing a new feature

1. Create `features/{module}/` + `{module}.feature` with appropriate tags.
2. Add module-specific steps in `features/steps/{module}_steps.py` (shared verbs already exist).
3. Add a CSV loader function in `src/entirius_tests/csv_loader.py` if needed.
4. Run `behave features/{module}/`; never hardcode channels, counts, or SKUs.

## Roadmap

- Phase 1 (complete): public API tests — matrix, CSV verification, prices, quantities, contentdb.
- Phase 2 (complete): authenticated admin CRUD (products, categories, features, feature sets, attributes).
- Phase 3 (planned): checkout v2 flow, public accounts, Playwright E2E (storefront PWA), load tests (k6).
