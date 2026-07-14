# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for advanced PIM scenarios.

Covers:
- Translation inheritance (pim_inheritance.feature)
- Product positions in categories (pim_category_products.feature)
- Signal-driven sync wait (signal_sync.feature)

Steps that use direct absolute URL paths (e.g. '/api/pim/v2/admin/channels/')
instead of the v2-path-relative helpers in admin_steps.py.
"""

from __future__ import annotations

import json
import time

from behave import given, then, when

from entirius_tests.assertions import assert_status

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


@given("I clear auth token")
def step_clear_auth_token(context) -> None:
    context.api.clear_auth_token()


# ---------------------------------------------------------------------------
# Direct absolute-URL requests (inheritance feature uses full /api/{module}/v2/... paths)
# ---------------------------------------------------------------------------


def _resolve_absolute_path(path: str, context) -> str:
    """Replace {channel_idx}, {default_channel_idx}, and {saved.*} placeholders."""
    resolved = path.replace("{channel_idx}", context.channel or "")
    default_idx = getattr(context, "default_channel_idx", "") or ""
    resolved = resolved.replace("{default_channel_idx}", default_idx)
    for key, val in (context.saved or {}).items():
        resolved = resolved.replace(f"{{{key}}}", str(val))
    return resolved


@when('I GET "{path}"')
@given('I GET "{path}"')
def step_get_absolute_url(context, path: str) -> None:
    resolved = _resolve_absolute_path(path, context)
    url = context.api.url(resolved)
    context.response = context.api.get(url)
    try:
        context.response_data = context.response.json()
    except Exception:
        context.response_data = {}


@when('I POST "{path}" with JSON:')
def step_post_absolute_url_json(context, path: str) -> None:
    resolved = _resolve_absolute_path(path, context)
    url = context.api.url(resolved)
    raw = _resolve_absolute_path(context.text, context)
    body = json.loads(raw)
    context.response = context.api.post(url, json=body)
    try:
        context.response_data = context.response.json()
    except Exception:
        context.response_data = {}


@when('I POST "{path}" with:')
def step_post_absolute_url_table(context, path: str) -> None:
    resolved = _resolve_absolute_path(path, context)
    url = context.api.url(resolved)
    body = {row[0]: _coerce_table_value(_resolve_absolute_path(row[1], context)) for row in context.table}
    context.response = context.api.post(url, json=body)
    try:
        context.response_data = context.response.json()
    except Exception:
        context.response_data = {}


@when('I PATCH "{path}" with:')
def step_patch_absolute_url_table(context, path: str) -> None:
    resolved = _resolve_absolute_path(path, context)
    url = context.api.url(resolved)
    body = {row[0]: _coerce_table_value(row[1]) for row in context.table}
    context.response = context.api.patch(url, json=body)
    try:
        context.response_data = context.response.json()
    except Exception:
        context.response_data = {}


def _coerce_table_value(value: str) -> bool | str:
    """Convert string table values to booleans where appropriate."""
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


# ---------------------------------------------------------------------------
# Alternate status assertion phrasing ("is N" vs "should be N")
# ---------------------------------------------------------------------------


@then("the response status is {status:d}")
def step_response_status_is(context, status: int) -> None:
    assert_status(context.response, status)


# ---------------------------------------------------------------------------
# Channel result assertions (pim_inheritance.feature @channels scenario)
# ---------------------------------------------------------------------------


@then('each channel result has field "{field}"')
def step_each_channel_result_has_field(context, field: str) -> None:
    results = context.response_data.get("results", [])
    assert results, "No results in channel response"
    for i, item in enumerate(results):
        assert field in item, f"Channel result {i} missing field '{field}'. Keys: {list(item.keys())}"


@then('exactly one channel has "{field}" equal to true')
def step_exactly_one_channel_field_true(context, field: str) -> None:
    results = context.response_data.get("results", [])
    assert results, "No results in channel response"
    matching = [item for item in results if item.get(field) is True]
    assert len(matching) == 1, f"Expected exactly 1 channel with '{field}' = true, got {len(matching)}"


# ---------------------------------------------------------------------------
# Alternate field assertion phrasing ("is true/not null" vs "should be ...")
# ---------------------------------------------------------------------------


@then('the response field "{field}" is true')
def step_field_is_true_alt(context, field: str) -> None:
    data = context.response_data
    assert field in data, f"Field '{field}' missing. Keys: {list(data.keys())}"
    assert data[field] is True, f"Expected '{field}' to be true, got {data[field]}"


@then('the response field "{field}" is not null')
def step_field_is_not_null_alt(context, field: str) -> None:
    data = context.response_data
    assert field in data, f"Field '{field}' missing. Keys: {list(data.keys())}"
    assert data[field] is not None, f"Expected '{field}' to not be null"


# ---------------------------------------------------------------------------
# Product precondition helpers (inheritance scenarios)
# ---------------------------------------------------------------------------


def _get_default_channel_idx(context) -> str:
    """Fetch the default channel idx from PIM admin channels endpoint."""
    if getattr(context, "default_channel_idx", None):
        return context.default_channel_idx
    url = context.api.url("api/pim/v2/admin/channels/")
    resp = context.api.get(url)
    assert resp.status_code == 200, f"Could not fetch channels: {resp.status_code} {resp.text[:200]}"
    data = resp.json()
    results = data.get("results", data) if isinstance(data, dict) else data
    for ch in results:
        if ch.get("is_default"):
            context.default_channel_idx = ch["idx"]
            return context.default_channel_idx
    raise AssertionError("No default channel found in PIM admin channels response")


def _ensure_product_on_channel(context, sku: str, channel_idx: str) -> None:
    """Create a minimal product on channel_idx if it does not already exist."""
    url = context.api.url(f"api/pim/v2/admin/{channel_idx}/products/{sku}/")
    resp = context.api.get(url)
    if resp.status_code == 200:
        return
    create_url = context.api.url(f"api/pim/v2/admin/{channel_idx}/products/")
    body = {"sku": sku, "feature_set_idx": "default", "is_enabled": True, "visibility": 4, "attributes": []}
    resp = context.api.post(create_url, json=body)
    assert resp.status_code in (200, 201), (
        f"Could not create product '{sku}' on channel '{channel_idx}': {resp.status_code} {resp.text[:300]}"
    )


@given('product "{sku}" exists on the default channel')
def step_product_exists_on_default_channel(context, sku: str) -> None:
    default_idx = _get_default_channel_idx(context)
    _ensure_product_on_channel(context, sku, default_idx)


@given('product "{sku}" exists on the default channel with name "{name}"')
def step_product_exists_on_default_channel_with_name(context, sku: str, name: str) -> None:
    default_idx = _get_default_channel_idx(context)
    _ensure_product_on_channel(context, sku, default_idx)
    url = context.api.url(f"api/pim/v2/admin/{default_idx}/products/{sku}/")
    context.api.patch(
        url,
        json={"attributes": [{"feature_idx": "name", "value_txt_t9n": {"en": name}}]},
    )


@given('product "{sku}" exists on channel "{channel_idx}"')
def step_product_exists_on_channel(context, sku: str, channel_idx: str) -> None:
    _ensure_product_on_channel(context, sku, channel_idx)


def _delete_product_from_channel(context, sku: str, channel_idx: str) -> None:
    """Delete a product from channel_idx if it exists (idempotent)."""
    url = context.api.url(f"api/pim/v2/admin/{channel_idx}/products/{sku}/")
    resp = context.api.get(url)
    if resp.status_code == 200:
        context.api.delete(url)


@given('product "{sku}" exists on the default channel only')
def step_product_exists_on_default_only(context, sku: str) -> None:
    default_idx = _get_default_channel_idx(context)
    # Remove from secondary channel if it leaked from a previous test run
    _delete_product_from_channel(context, sku, "default-europe")
    _ensure_product_on_channel(context, sku, default_idx)


@given('product "{sku}" exists on both channels')
def step_product_exists_on_both_channels(context, sku: str) -> None:
    default_idx = _get_default_channel_idx(context)
    _ensure_product_on_channel(context, sku, default_idx)
    _ensure_product_on_channel(context, sku, "default-europe")


@given('product "{sku}" on "{channel_idx}" has inheritance enabled')
def step_product_has_inheritance_enabled(context, sku: str, channel_idx: str) -> None:
    _ensure_product_on_channel(context, sku, channel_idx)
    url = context.api.url(f"api/pim/v2/admin/{channel_idx}/products/{sku}/")
    context.api.patch(url, json={"inherit_attributes": True, "inherit_descriptions": True})


@given('product "{sku}" on "{channel_idx}" has description inheritance enabled')
def step_product_has_description_inheritance_enabled(context, sku: str, channel_idx: str) -> None:
    _ensure_product_on_channel(context, sku, channel_idx)
    url = context.api.url(f"api/pim/v2/admin/{channel_idx}/products/{sku}/")
    context.api.patch(url, json={"inherit_descriptions": True})


@given('product "{sku}" on "{channel_idx}" inherits from default')
def step_product_inherits_from_default(context, sku: str, channel_idx: str) -> None:
    step_product_has_inheritance_enabled(context, sku, channel_idx)


@when('I PATCH the default channel product "{sku}" name to "{name}"')
def step_patch_default_channel_product_name(context, sku: str, name: str) -> None:
    default_idx = _get_default_channel_idx(context)
    url = context.api.url(f"api/pim/v2/admin/{default_idx}/products/{sku}/")
    context.response = context.api.patch(
        url,
        json={"attributes": [{"feature_idx": "name", "value_txt_t9n": {"en": name}}]},
    )
    try:
        context.response_data = context.response.json()
    except Exception:
        context.response_data = {}


@then('the product name contains "{name}"')
def step_product_name_contains(context, name: str) -> None:
    data = context.response_data
    # Name may be in attributes list or in a top-level name field
    raw_name = data.get("name") or data.get("name_t9n", {})
    if isinstance(raw_name, dict):
        text_values = list(raw_name.values())
    elif isinstance(raw_name, str):
        text_values = [raw_name]
    else:
        # Search in attributes
        attrs = data.get("attributes", [])
        text_values = []
        for attr in attrs:
            if attr.get("feature_idx") == "name":
                vals = attr.get("values", {})
                if isinstance(vals, dict):
                    text_values.extend(vals.values())
    assert any(name in str(v) for v in text_values), f"Expected product name to contain '{name}'. Found: {text_values}"


# ---------------------------------------------------------------------------
# Category-products list assertions
# ---------------------------------------------------------------------------


@then('the results list "{list_field}" should have at least {count:d} items')
def step_results_list_min_items(context, list_field: str, count: int) -> None:
    data = context.response_data
    assert list_field in data, f"Field '{list_field}' missing. Keys: {list(data.keys())}"
    items = data[list_field]
    assert isinstance(items, list), f"Field '{list_field}' is not a list, got {type(items).__name__}"
    assert len(items) >= count, f"Expected '{list_field}' to have at least {count} items, got {len(items)}"


@then('I save the nested field "{path}" as "{alias}"')
def step_save_nested_field(context, path: str, alias: str) -> None:
    """Save a nested value using dot notation with list index support.

    Example: 'unpositioned.0.sku' accesses response_data['unpositioned'][0]['sku'].
    """
    data = context.response_data
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, list):
            try:
                idx = int(part)
            except ValueError:
                raise AssertionError(f"Expected integer list index at '{part}' in path '{path}', got non-integer")
            assert idx < len(current), f"Index {idx} out of range for list of length {len(current)} at path '{path}'"
            current = current[idx]
        elif isinstance(current, dict):
            assert part in current, f"Key '{part}' missing at path '{path}'. Available: {list(current.keys())}"
            current = current[part]
        else:
            raise AssertionError(f"Cannot traverse '{part}' on {type(current).__name__} at path '{path}'")
    context.saved[alias] = current


@then('the list "{list_field}" should contain an item with "{key}" equal to "{value}"')
def step_list_field_contains_item(context, list_field: str, key: str, value: str) -> None:
    """Assert a top-level list field contains an item matching key=value.

    Resolves {saved.*} placeholders in value.
    """
    resolved_value = value
    for saved_key, saved_val in (context.saved or {}).items():
        resolved_value = resolved_value.replace(f"{{{saved_key}}}", str(saved_val))

    data = context.response_data
    assert list_field in data, f"Field '{list_field}' missing. Keys: {list(data.keys())}"
    items = data[list_field]
    assert isinstance(items, list), f"Field '{list_field}' is not a list"
    found = any(str(item.get(key)) == resolved_value for item in items)
    assert found, (
        f"No item with '{key}' = '{resolved_value}' in '{list_field}'. Values: {[item.get(key) for item in items[:10]]}"
    )


# ---------------------------------------------------------------------------
# Signal sync wait
# ---------------------------------------------------------------------------


@when("I wait {seconds:d} seconds")
def step_wait_seconds(context, seconds: int) -> None:
    time.sleep(seconds)
