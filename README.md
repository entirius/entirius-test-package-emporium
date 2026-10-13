# entirius-test-package-emporium

The test package of Entirius, the open-source modular ecommerce platform: a demo dataset plus the BDD and
end-to-end suites that verify a backend against it. One repository, two halves that depend on each other.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://github.com/entirius/entirius-test-package-emporium/blob/develop/pyproject.toml)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-test-package-emporium/blob/develop/LICENSE)

## What it does

- Ships the Emporium demo dataset (`package/`, `fixtures/`, `images/`): channels, products, prices, quantities and
  discount rules that seed a fresh database, so the API works at once.
- Verifies a running backend with behave (Gherkin) scenarios in `features/`; every expected value is read from the
  dataset's CSV files, none is hardcoded.
- Covers the public API and the authenticated admin API, by module, selected with tags.
- Drives the storefront and the admin CMS with Playwright end-to-end suites in `e2e/`.
- Builds a data package in the same layout from your own catalog file.

## Installation

```bash
git clone https://github.com/entirius/entirius-test-package-emporium.git
cd entirius-test-package-emporium
make install     # uv sync, every extra
```

## Quick start

```bash
make test                    # behave dry-run + unit tests: steps bind, no API needed
make bdd TAGS=@matrix-v2     # one tag against a seeded backend (API_BASE_URL, default http://localhost:8000)
make bdd                     # the full suite
make e2e                     # Playwright suites against live frontends
```

`make bdd` needs a running backend seeded with this package: `scripts/seed.sh` does the seeding, and the
entirius-zeno harness (https://github.com/entirius/entirius-zeno) starts a stack and seeds it with this package.
`make e2e` needs browsers once: `uv run --extra e2e playwright install chromium`.

Configuration comes from environment variables, `behave.ini` (gitignored; copy `behave.ini.example`) or channel
auto-discovery, in that order:
https://github.com/entirius/entirius-test-package-emporium/blob/develop/docs/configuration.md

## Requirements

- Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).
- For `make bdd`: a running Entirius backend seeded with this package.
- For `make e2e`: the storefront and the admin CMS running (`E2E_BASE_URL`, `CMS_BASE_URL`) and Playwright's
  Chromium.

## Documentation

- Package docs (configuration, tags, writing features, harness, data package):
  https://github.com/entirius/entirius-test-package-emporium/tree/develop/docs
- Dataset details (channels, catalog, import pipeline):
  https://github.com/entirius/entirius-test-package-emporium/blob/develop/package/README.md
- Entirius documentation: https://docs.entirius.com/
- Releases: https://github.com/entirius/entirius-test-package-emporium/releases

## Part of Entirius

The package is an external consumer of the platform: it seeds the backend and tests it over HTTP.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Frontends under test: https://github.com/entirius/entirius-pwa-storefront,
  https://github.com/entirius/entirius-pwa-cms

## Development

```bash
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # behave dry-run + unit tests
```

Development and agent instructions:
https://github.com/entirius/entirius-test-package-emporium/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see
https://github.com/entirius/entirius-test-package-emporium/blob/develop/LICENSE.
