# AGENTS.md

`entirius-test-package-emporium` (import `entirius_tests`) — the test package of Entirius: the Emporium demo dataset
and the BDD suite that verifies it. Tests both the public API (CSV-imported data verification) and the authenticated
admin API (CRUD); runs as an external consumer against a running backend seeded with `package/`.

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
| `make data-package PROFILE=… CATALOG=… OUT=… [MOUNT=…]` | build, then validate, a data package from a profile and a JSON or CSV catalog (`python -m entirius_tests.data_package`, extra `data`; `docs/data-package.md`) |

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
- **One-shot scenarios** (`@lookup-oneshot`, `@leads-oneshot`, `@communicator-oneshot`, `@toolbox-oneshot`) mutate a
  pre-seeded row once per database: a BDD re-run needs a fresh seed (`docs/harness.md`).
- No AI attribution in commits or PR descriptions.

## Architecture

```
├── src/entirius_tests/     # Shared library (installed by `uv sync`)
│   ├── api_client.py       # HTTP client (GET/POST/PATCH/DELETE + JWT auth)
│   ├── auth.py             # JWT token acquisition
│   ├── csv_loader.py       # Parse CSV from package/
│   ├── assertions.py       # Assert helpers + extract_items()
│   ├── mail.py             # GreenMail sandbox: purge/count/read (REST), send (SMTP), inject (IMAP APPEND)
│   ├── clock.py            # communicator dev-only test endpoints: channel clock, send-due, poll-now
│   └── data_package/       # profile.yaml + catalog (JSON/CSV) -> package/, fixtures/, images/ (build, validate); no network
├── features/               # Behave BDD features
│   ├── environment.py      # before_all: API client + channels; before_scenario: reset + clear auth
│   ├── steps/              # Shared step definitions (HTTP verbs, assertions, admin CRUD, domains)
│   ├── admin/  suppliers/  matrix/  matrix_v2/  pim_csv/  checkout/  lookup/
│   └── contentdb/  pricemanager/  qms/  faq/  deliverypoints/  agreements/  contact_forms/
├── package/                # Emporium demo dataset (CSV; see package/README.md)
├── fixtures/               # Django YAML fixtures (loaddata)
│   ├── mail/               # hand-written .eml: replies, autoresponder, opt-outs, DSN hard/soft, duplicate
│   ├── siteintel/          # anonymised PSI/URLScan recordings (psi/, urlscan/) + synthetic sites/{good,slow,broken}
│   └── lookup/             # Calibration set: pim_products.json, atlas_products.json,
│                           # labelled_pairs.csv, img/*.png — see scripts/generate-lookup-fixtures.py
├── images/                 # Product images per SKU
├── examples/data-package/  # example profile, the same catalog as JSON and CSV, three images
├── devtools/               # Bulk data multiplier (stress tests)
├── scripts/                # Seed (host) + import (container) + behave.ini generator
│   ├── anonymise-siteintel-recordings.py  # private export -> fixtures/siteintel (mapping to stdout only);
│   │                                      # --verify fixtures/siteintel = leak gate only (.gitleaks.toml words, hosts, emails, IPs)
│   ├── generate-lookup-fixtures.py  # deterministic (fixed seed) — regenerate + commit, not run at seed time
│   ├── installed-apps.py            # enabled app labels, one per line — the one app list of a seed run
│   ├── seed-access.py               # seed.sh Step 3e — role staff users (docs/configuration.md); Step 4b imports legacy keys
│   ├── secret_scan.py               # stdin → counts of ent_api_ tokens + legacy fixture keys (never a match); exit 1 on any
│   └── seed-lookup.py               # seed.sh Step 6z — loads fixtures/lookup/, backfills, seeds one proposal
├── tests/                  # pytest for scripts/ (`uv run --extra e2e pytest tests/`)
├── e2e/                    # Playwright E2E (cms/, storefront/; conftest.py = E2E_DEVICE emulation)
│                           # leads funnel (page objects, determinism, harness commands): docs/e2e-leads-funnel.md
└── load/k6/                # placeholder for k6 load tests (empty)
```

The seed and the suite follow the modules the backend enables: `scripts/seed.sh` guards every step by app
(`SEED_PROFILE`, `SEED_APPS`, `--dry-run`), and `before_feature` skips a feature whose module the public registry does
not list (`entirius_tests.munin.FEATURE_MODULES`; `tests/test_feature_modules.py` fails on an unmapped file).

| Topic | Where |
|---|---|
| Settings, `behave.ini`, channel discovery, reports | `docs/configuration.md` |
| Tag taxonomy, tags with preconditions | `docs/tags.md` |
| Step patterns, writing a new feature | `docs/writing-features.md` |
| API endpoints under test | `docs/api-under-test.md` |
| Seed, harness targets, one-shot scenarios, module subsets | `docs/harness.md` |
| Data package from your own catalog | `docs/data-package.md` |
| Leads funnel end-to-end | `docs/e2e-leads-funnel.md` |
| Emporium universe (brand, series, copy tone) | `docs/brandbook.md` |
| Operator checklists | `docs/operator-atlas.md`, `docs/operator-pricefighter.md` |
| Dataset details, discount rules | `package/README.md`, `DISCOUNT_RULES.md` |

## Settings

`behave.ini` is gitignored — copy `behave.ini.example` or generate via
`scripts/generate-behave-ini.sh`. Priority: env vars > `behave.ini` `[behave.userdata]` >
auto-discovery (`discover_channels()` scans `products--{channel}.csv` filenames).
Keys, env vars and defaults: `docs/configuration.md`.
