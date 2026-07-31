.PHONY: help install check fix test bdd e2e
.DEFAULT_GOAL := help

help:  ## List targets
	@grep -E '^[a-z-]+:.*##' $(firstword $(MAKEFILE_LIST)) | awk -F':.*##' '{printf "  %-16s %s\n", $$1, $$2}'
install:  ## Sync dependencies (uv, incl. extras)
	uv sync --all-extras
check:  ## Lint + format-check (ruff) + canonical .gitleaks.toml
	@grep -q "forbidden-names" .gitleaks.toml 2>/dev/null || { echo "Missing or non-canonical .gitleaks.toml - symlink the config per the internal secret-scanning standard"; exit 1; }
	uv run ruff check .
	uv run ruff format --check .
fix:  ## Auto-fix lint + format
	uv run ruff check --fix .
	uv run ruff format .
# Excluded by default: @spec-first (scenarios ahead of their module),
# @blocked-by-module (known module gaps — see the internal debt registry).
EXCLUDES = --tags=-@spec-first --tags=-@blocked-by-module
test:  ## Bind steps to scenarios without hitting an API (behave dry-run)
	uv run behave --dry-run $(EXCLUDES) --no-summary -f progress
bdd:  ## Run BDD suite against a live API (API_BASE_URL, TAGS optional)
	uv run behave $(EXCLUDES) $(if $(TAGS),--tags=$(TAGS),)
E2E_BASE_URL ?= http://localhost:3100
e2e:  ## Run e2e suites against live PWAs (E2E_BASE_URL = storefront; CMS_BASE_URL, API_BASE_URL via env)
	uv run pytest e2e/ --base-url $(E2E_BASE_URL)
