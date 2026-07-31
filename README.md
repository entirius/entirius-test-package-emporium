# entirius-test-package-emporium

BDD test suite and demo data package for the Entirius/Volkanos platform.
One repo, two halves that depend on each other:

- `package/` + `fixtures/` + `images/` — the **Emporium demo dataset**: channels, products, prices,
  quantities, discount rules. Seeds a fresh database so the API is immediately functional.
- `features/` + `src/entirius_tests/` — **behave (Gherkin) tests** that verify a running service
  against that dataset. All assertions are derived from the CSV data — zero hardcoded expected values.

## Quick start

Prerequisites: a running Volkanos backend seeded with this package (see `scripts/`),
Python 3.11+ with uv.

```bash
make install                 # uv sync (creates .venv)
make check                   # ruff lint + format check
make test                    # behave dry-run: steps bind, no API needed
make bdd                     # full suite against a live API
make bdd TAGS=@matrix-v2     # by tag
make e2e                     # Playwright e2e (storefront + CMS) against live frontends
```

`make e2e` needs browsers once: `uv run playwright install chromium`. Frontend URLs:
`E2E_BASE_URL` (storefront, default `:3100`), `CMS_BASE_URL` (default `:8180`).

Configuration comes from environment variables, `behave.ini` (gitignored — copy
`behave.ini.example`), or auto-discovery, in that priority order.

### Key settings

| Key | Env var | Default | Description |
|-----|---------|---------|-------------|
| `api_base_url` | `API_BASE_URL` | `http://localhost:8000` | Volkanos API URL |
| `api_version` | `API_VERSION` | `1` | API version |
| `test_package_path` | `TEST_PACKAGE_PATH` | `package` | Path to CSV test data |
| `channels` | `CHANNELS` | auto-discover | Comma-separated channel list |
| `primary_channel` | `PRIMARY_CHANNEL` | first channel | Default channel for single-channel tests |
| `admin_username` | `ADMIN_USERNAME` | `admin` | Admin superuser for JWT auth |
| `admin_password` | `ADMIN_PASSWORD` | `admin123` | Admin password |
| `test_username` | `TEST_USERNAME` | `testuser` | Regular (non-admin) user for auth tests |
| `test_password` | `TEST_PASSWORD` | `testuser123` | Regular user password |

Channel auto-discovery scans `test_package_path` for `products--{channel}.csv` filenames.
Point `test_package_path` at any directory with the standard CSV layout to switch datasets.

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
| `@spec-first` | Scenarios written ahead of step implementation — excluded from `make test`/`make bdd` |

## Layout

```
├── package/            # Importable CSV data (products, categories, prices, qty, feeds)
├── fixtures/           # Django YAML fixtures (loaddata)
├── images/             # Product images per SKU
├── devtools/           # Bulk data multiplier for stress testing
├── scripts/            # Seed and import scripts (host + container side)
├── features/           # Behave BDD features + step definitions
├── src/entirius_tests/ # Shared test library (API client, CSV loader, assertions)
├── e2e/                # Playwright e2e (storefront order flow, CMS order visibility)
└── load/               # Load tests (planned)
```

Dataset details (channels, catalog, import pipeline): [`package/README.md`](package/README.md).
Discount rules: [`DISCOUNT_RULES.md`](DISCOUNT_RULES.md).

## Reports

JUnit XML output goes to `reports/` (gitignored). Used for CI integration.

## License

MPL-2.0
