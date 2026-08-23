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
| `make test` | behave dry-run — steps bind to scenarios, no API needed |
| `make bdd [TAGS=@tag]` | full BDD suite against a live API (`API_BASE_URL`) |

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
- **One-shot scenarios** (`@lookup-oneshot` here; also suppliers audit-trail, atlas push/merge):
  mutate a specific pre-seeded row once per database — re-running them against an already-consumed
  DB fails on purpose. A BDD re-run needs a fresh `make seed` (zeno `AGENTS.md` §Green baselines).

## Architecture

```
├── src/entirius_tests/     # Shared library (pip install -e .)
│   ├── api_client.py       # HTTP client (GET/POST/PATCH/DELETE + JWT auth)
│   ├── auth.py             # JWT token acquisition
│   ├── csv_loader.py       # Parse CSV from package/
│   └── assertions.py       # Assert helpers + extract_items()
├── features/               # Behave BDD features
│   ├── environment.py      # before_all: API client + channels; before_scenario: reset + clear auth
│   ├── steps/              # Shared step definitions (HTTP verbs, assertions, admin CRUD, domains)
│   ├── admin/  suppliers/  matrix/  matrix_v2/  pim_csv/  checkout/  lookup/
│   └── contentdb/  pricemanager/  qms/  faq/  deliverypoints/  agreements/  contact_forms/
├── package/                # Emporium demo dataset (CSV; see package/README.md)
├── fixtures/               # Django YAML fixtures (loaddata)
│   └── lookup/             # Calibration set (dev-plan 09): pim_products.json, atlas_products.json,
│                           # labelled_pairs.csv, img/*.png — see scripts/generate-lookup-fixtures.py
├── images/                 # Product images per SKU
├── devtools/               # Bulk data multiplier (stress tests)
├── scripts/                # Seed (host) + import (container) + behave.ini generator
│   ├── generate-lookup-fixtures.py  # deterministic (fixed seed) — regenerate + commit, not run at seed time
│   └── seed-lookup.py               # seed.sh Step 6z — loads fixtures/lookup/, backfills, seeds one proposal
├── e2e/                    # Playwright E2E (planned)
└── load/                   # Load tests k6 (planned)
```

## Configuration

`behave.ini` is gitignored — copy `behave.ini.example` or generate via
`scripts/generate-behave-ini.sh`. Priority: env vars > `behave.ini` `[behave.userdata]` >
auto-discovery (`discover_channels()` scans `products--{channel}.csv` filenames).
Key settings table: see `README.md`.

## Step patterns (essentials)

- Public (CSV-driven): `the channel is the primary channel`, `the response count should match
  CSV product count`, `the CSV attributes should be non-empty`.
- ContentDB: `I GET the ContentDB published endpoint "{path}"` (+ `with channel` / `with routes`).
- ContentDB admin v1 (JWT, `/api-admin/` prefix — not the v2 `/api/` shape):
  `I GET/DELETE the ContentDB admin endpoint "{path}" [without auth]`.
- Admin v2 (JWT): `Given I am authenticated as an admin/regular user`;
  `When I GET/POST/PATCH/DELETE the v2 admin endpoint "{path}" [with body|with params|without auth]`.
- Assertions: `the response field "{field}" should equal/be true/be null/be a dict…`,
  `the results should contain an item with "{key}" equal to "{value}"`,
  `I save the response field "{field}" as "{alias}"`.

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
- Lookup (`@lookup`, `features/lookup/lookup_check.feature`): `lookup/admin/search/` and
  `lookup/admin/check/` (JSON or multipart `image` file), reused generic v2-admin steps for
  everything except the multipart upload and the `hits`/`candidates`/`possible_duplicates`
  "contains a candidate for `<ref>`" assertion (`features/steps/lookup_steps.py` — the lookup API's
  lists are never the generic `results` shape). Also exercises the PIM create-hook
  (`possible_duplicates` in the create-product response, plan 07) and, `@lookup-oneshot`, the
  `duplicate_in_pim` enrichment proposal accept (`enrichment/admin/proposals/`, plan 06) —
  `ContentProposal.status` becomes `applied`, not `accepted`, on accept.

## Writing a new feature

1. Create `features/{module}/` + `{module}.feature` with appropriate tags.
2. Add module-specific steps in `features/steps/{module}_steps.py` (shared verbs already exist).
3. Add a CSV loader function in `src/entirius_tests/csv_loader.py` if needed.
4. Run `behave features/{module}/`; never hardcode channels, counts, or SKUs.

## Roadmap

- Phase 1 (complete): public API tests — matrix, CSV verification, prices, quantities, contentdb.
- Phase 2 (complete): authenticated admin CRUD (products, categories, features, feature sets, attributes).
- Phase 3 (planned): checkout v2 flow, public accounts, Playwright E2E (storefront PWA), load tests (k6).
