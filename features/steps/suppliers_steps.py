# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for django-suppliers BDD tests.

Idempotent cleanup helpers + module-specific assertions. Mirrors the
`deliverypoints_steps.py` and `faq_steps.py` patterns: find by string identifier
via list endpoint, delete by integer PK or slug.

All HTTP via `context.api` (JWT-aware client set up by `admin_steps`).
Test data prefix: `bdd-` to avoid collision with `demo-supplier` fixture.
"""

from __future__ import annotations

import time

from behave import given, then, when

_BASE = "api/suppliers/v2/admin"
_REGIONAL = "api/regional/v2/admin"


# ---------------------------------------------------------------------------
# Regional reference lookups (resolve iso codes -> PK for supplier payloads)
# ---------------------------------------------------------------------------


def _store_regional_id(context, resource: str, match_field: str, match_value: str, alias: str) -> None:
    """Fetch /regional/v2/admin/{resource}/ and store the row's id into context.saved[alias]."""
    url = context.api.url(f"{_REGIONAL}/{resource}/")
    resp = context.api.get(url)
    assert resp.status_code == 200, f"GET {url} failed: {resp.status_code} {resp.text[:200]}"
    rows = resp.json().get("results", [])
    match = next((r for r in rows if str(r.get(match_field, "")).lower() == match_value.lower()), None)
    assert match, f"{resource}: no row with {match_field}={match_value!r} (have {len(rows)})"
    context.saved[alias] = match["id"]


@given('regional language "{iso2}" id is stored as "{alias}"')
def step_store_language_id(context, iso2, alias):
    _store_regional_id(context, "languages", "iso2", iso2, alias)


@given('regional currency "{iso3}" id is stored as "{alias}"')
def step_store_currency_id(context, iso3, alias):
    _store_regional_id(context, "currencies", "iso3", iso3, alias)


@given('regional country "{iso2}" id is stored as "{alias}"')
def step_store_country_id(context, iso2, alias):
    _store_regional_id(context, "countries", "iso2", iso2, alias)


# ---------------------------------------------------------------------------
# Cleanup helpers (idempotent — accept 200/204/404)
# ---------------------------------------------------------------------------


@given('I ensure supplier with idx "{idx}" is cleaned up')
def step_ensure_supplier_cleaned(context, idx):
    """Hard-delete supplier with cascade. Accept 404 if not present."""
    url = context.api.url(f"{_BASE}/suppliers/{idx}/?force=true")
    context.api.delete(url)


@given('I ensure feed "{idx}" for supplier "{supplier_idx}" is cleaned up')
def step_ensure_feed_cleaned(context, idx, supplier_idx):
    url = context.api.url(f"{_BASE}/suppliers/{supplier_idx}/feeds/{idx}/")
    context.api.delete(url)


@given('I ensure mapping profile "{idx}" for supplier "{supplier_idx}" is cleaned up')
def step_ensure_profile_cleaned(context, idx, supplier_idx):
    url = context.api.url(f"{_BASE}/suppliers/{supplier_idx}/mapping-profiles/{idx}/")
    context.api.delete(url)


@given('I ensure supplier product with external_id "{eid}" for supplier "{supplier_idx}" is cleaned up')
def step_ensure_sp_cleaned(context, eid, supplier_idx):
    """Find SupplierProduct by external_id via list, delete by PK if exists."""
    url = context.api.url(f"{_BASE}/products/")
    resp = context.api.get(url, params={"supplier_idx": supplier_idx, "search": eid, "page_size": 100})
    if resp.status_code != 200:
        return
    for item in resp.json().get("results", []):
        if item.get("external_id") == eid:
            del_url = context.api.url(f"{_BASE}/products/{item['id']}/")
            context.api.delete(del_url)
            return


@given('I ensure product supplier link for sku "{sku}" supplier "{supplier_idx}" is cleaned up')
def step_ensure_link_cleaned(context, sku, supplier_idx):
    url = context.api.url(f"{_BASE}/product-links/")
    resp = context.api.get(url, params={"real_product_sku": sku, "supplier_idx": supplier_idx, "page_size": 100})
    if resp.status_code != 200:
        return
    for item in resp.json().get("results", []):
        if item.get("real_product_sku") == sku and item.get("supplier_idx") == supplier_idx:
            del_url = context.api.url(f"{_BASE}/product-links/{item['id']}/")
            context.api.delete(del_url)
            return


# ---------------------------------------------------------------------------
# Domain-specific assertions / helpers
# ---------------------------------------------------------------------------


@then('the response should include integration event with type "{event_type}"')
def step_response_includes_event_type(context, event_type):
    """Used after delete-impact / push responses that bundle emitted events."""
    data = context.response_data
    events = data.get("events") or data.get("emitted_events") or []
    types = [e.get("event_type") for e in events]
    assert event_type in types, f"Expected event_type {event_type!r} in {types}"


@then('the events list should contain at least one event of type "{event_type}"')
def step_events_list_has_type(context, event_type):
    results = context.response_data.get("results", context.response_data)
    if isinstance(results, dict):
        results = results.get("results", [])
    matching = [e for e in results if e.get("event_type") == event_type]
    assert matching, (
        f"No event of type {event_type!r} in response. Got types: {[e.get('event_type') for e in results[:10]]}"
    )


@then('the response field "results" should contain at least {n:d} item')
@then('the response field "results" should contain at least {n:d} items')
def step_results_at_least(context, n):
    results = context.response_data.get("results", [])
    assert len(results) >= n, f"Expected >= {n} results, got {len(results)}"


@then('the response field "{field}" should contain {n:d} items')
def step_field_exact_count(context, field, n):
    value = context.response_data.get(field)
    assert isinstance(value, list), f"Field {field!r} is not a list: {type(value).__name__}"
    assert len(value) == n, f"Expected exactly {n} items in {field!r}, got {len(value)}"


@then('the response field "{field}" should be an empty list')
def step_field_empty_list(context, field):
    value = context.response_data.get(field)
    assert isinstance(value, list), f"Field {field!r} is not a list: {type(value).__name__}"
    assert len(value) == 0, f"Expected empty list for {field!r}, got {len(value)} items"


@when('I wait up to {timeout:d} seconds for supplier product {pk:d} to reach status "{expected}"')
def step_wait_sp_status(context, timeout, pk, expected):
    """Poll real backend until SupplierProduct.status matches (Celery async tolerance)."""
    deadline = time.time() + timeout
    last_status = None
    while time.time() < deadline:
        url = context.api.url(f"{_BASE}/products/{pk}/")
        resp = context.api.get(url)
        if resp.status_code == 200:
            last_status = resp.json().get("status")
            if last_status == expected:
                context.response = resp
                context.response_data = resp.json()
                return
        time.sleep(1)
    raise AssertionError(
        f"SupplierProduct {pk} did not reach status {expected!r} within {timeout}s (last seen: {last_status!r})"
    )
