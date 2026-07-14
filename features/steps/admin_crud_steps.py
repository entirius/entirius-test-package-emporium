# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for admin API v2 CRUD operations."""

from __future__ import annotations

import json

from behave import given, then, when


def _resolve_placeholders(text: str, context) -> str:
    """Replace {channel_idx} and {saved.*} placeholders in any string."""
    resolved = text.replace("{channel_idx}", context.channel or "")
    for key, val in (context.saved or {}).items():
        resolved = resolved.replace(f"{{{key}}}", str(val))
    return resolved


def _resolve_path(path: str, context) -> str:
    """Replace {channel_idx} and {saved.*} placeholders in URL path."""
    return _resolve_placeholders(path, context)


def _convert_v2_url(path: str) -> str:
    """Build api/{module}/v2/{rest} from a step path like 'pim/admin/...' or 'agreements/...'."""
    parts = path.split("/", 1)
    module = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    return f"api/{module}/v2/{rest}"


# --- Write Operations ---


@when('I POST to the v2 admin endpoint "{path}" with body')
def step_post_v2_admin(context, path):
    resolved = _resolve_path(path, context)
    url = context.api.url(_convert_v2_url(resolved))
    body = json.loads(_resolve_placeholders(context.text, context))
    context.response = context.api.post(url, json=body)
    context.response_data = context.response.json()


@when('I PATCH the v2 admin endpoint "{path}" with body')
def step_patch_v2_admin(context, path):
    resolved = _resolve_path(path, context)
    url = context.api.url(_convert_v2_url(resolved))
    body = json.loads(_resolve_placeholders(context.text, context))
    context.response = context.api.patch(url, json=body)
    context.response_data = context.response.json()


@when('I DELETE the v2 admin endpoint "{path}"')
def step_delete_v2_admin(context, path):
    resolved = _resolve_path(path, context)
    url = context.api.url(_convert_v2_url(resolved))
    context.response = context.api.delete(url)
    if context.response.status_code == 204:
        context.response_data = {}
    else:
        context.response_data = context.response.json()


@when('I DELETE the v2 admin endpoint "{path}" with body')
def step_delete_v2_admin_with_body(context, path):
    resolved = _resolve_path(path, context)
    url = context.api.url(_convert_v2_url(resolved))
    body = json.loads(_resolve_placeholders(context.text, context))
    context.response = context.api.delete(url, json=body)
    if context.response.status_code == 204:
        context.response_data = {}
    else:
        context.response_data = context.response.json()


# --- Cleanup (idempotent delete, ignore 404) ---


@given('I ensure v2 admin resource "{path}" is deleted')
def step_ensure_deleted(context, path):
    resolved = _resolve_path(path, context)
    url = context.api.url(_convert_v2_url(resolved))
    resp = context.api.delete(url)
    # Accept 200 (deleted), 204 (soft-deleted), 404 (already gone), or 500 (data pollution)
    if resp.status_code == 500:
        # Data pollution from previous run -- try to continue
        return
    assert resp.status_code in (200, 204, 404), f"Cleanup failed for {resolved}: {resp.status_code} {resp.text[:200]}"
    # For soft-delete modules: try hard-delete via ?hard=true query param
    if resp.status_code == 204:
        context.api.delete(url + "?hard=true")


@given('I ensure agreement definition "{slug}" is hard-deleted')
def step_ensure_agreement_hard_deleted(context, slug):
    """Hard-delete agreement definition via admin API, bypassing soft-delete."""
    url = context.api.url(f"api/agreements/v2/admin/definitions/{slug}/")
    context.api.delete(url)  # soft-delete first
    context.api.delete(url + "?hard=true")  # try hard-delete


# --- Save/Reference Context ---


@then('I save the response field "{field}" as "{alias}"')
def step_save_field(context, field, alias):
    data = context.response_data
    assert field in data, f"Cannot save '{field}': not in response. Keys: {list(data.keys())}"
    context.saved[alias] = data[field]


@then('I save the first result field "{field}" as "{alias}"')
def step_save_first_result_field(context, field, alias):
    results = context.response_data.get("results", [])
    assert results, "No results to save from"
    assert field in results[0], f"Field '{field}' not in first result. Keys: {list(results[0].keys())}"
    context.saved[alias] = results[0][field]


# --- Field Assertions ---


@then('the response field "{field}" should equal "{value}"')
def step_field_equals_str(context, field, value):
    data = context.response_data
    value = _resolve_placeholders(value, context)  # e.g. code == "manual-{channel_idx}"
    assert field in data, f"Field '{field}' missing. Keys: {list(data.keys())}"
    actual = str(data[field])
    assert actual == value, f"Expected '{field}' = '{value}', got '{actual}'"


@then('the response field "{field}" should equal integer {value:d}')
def step_field_equals_int(context, field, value):
    data = context.response_data
    assert field in data, f"Field '{field}' missing. Keys: {list(data.keys())}"
    assert data[field] == value, f"Expected '{field}' = {value}, got {data[field]}"


@then('the response field "{field}" should be true')
def step_field_is_true(context, field):
    data = context.response_data
    assert field in data, f"Field '{field}' missing"
    assert data[field] is True, f"Expected '{field}' to be true, got {data[field]}"


@then('the response field "{field}" should be false')
def step_field_is_false(context, field):
    data = context.response_data
    assert field in data, f"Field '{field}' missing"
    assert data[field] is False, f"Expected '{field}' to be false, got {data[field]}"


@then('the response field "{field}" should not be null')
def step_field_not_null(context, field):
    data = context.response_data
    assert field in data, f"Field '{field}' missing"
    assert data[field] is not None, f"Expected '{field}' to not be null"


@then('the response field "{field}" should be null')
def step_field_is_null(context, field):
    data = context.response_data
    assert field in data, f"Field '{field}' missing"
    assert data[field] is None, f"Expected '{field}' to be null, got {data[field]}"


@then('the response field "{field}" should be a dict')
def step_field_is_dict(context, field):
    data = context.response_data
    assert field in data, f"Field '{field}' missing"
    assert isinstance(data[field], dict), f"Expected '{field}' to be a dict, got {type(data[field]).__name__}"


@then('the response field "{field}" should be a list')
def step_field_is_list(context, field):
    data = context.response_data
    assert field in data, f"Field '{field}' missing"
    assert isinstance(data[field], list), f"Expected '{field}' to be a list, got {type(data[field]).__name__}"


# --- Results Assertions ---


def _extract_results(response_data):
    """Extract results list from paginated dict or plain list response."""
    if isinstance(response_data, list):
        return response_data
    return response_data.get("results", [])


@then("the results count should be greater than {count:d}")
def step_results_count_gt(context, count):
    data = context.response_data
    if isinstance(data, list):
        actual = len(data)
    else:
        actual = data.get("count", 0)
    assert actual > count, f"Expected count > {count}, got {actual}"


@then('the results should contain an item with "{key}" equal to "{value}"')
def step_results_contain_item(context, key, value):
    results = _extract_results(context.response_data)
    found = any(str(item.get(key)) == value for item in results)
    assert found, f"No item with '{key}' = '{value}' in results. Values: {[item.get(key) for item in results[:10]]}"


@then('the results should not contain an item with "{key}" equal to "{value}"')
def step_results_not_contain_item(context, key, value):
    results = _extract_results(context.response_data)
    found = any(str(item.get(key)) == value for item in results)
    assert not found, f"Item with '{key}' = '{value}' should not exist in results"


# --- Nested Field Assertions ---


def _walk_nested(data, path: str):
    """Walk a dotted path through dicts and lists.

    Numeric segments are treated as list indices; everything else as dict keys.
    Examples: 'name_t9n.en', 'warnings.0.code'.
    """
    keys = path.split(".")
    current = data
    for k in keys:
        if k.isdigit() and isinstance(current, list):
            idx = int(k)
            assert idx < len(current), f"Index {idx} out of range for list of length {len(current)} at '{k}'"
            current = current[idx]
        else:
            assert isinstance(current, dict), f"Expected dict at '{k}', got {type(current)}"
            assert k in current, f"Key '{k}' missing in {list(current.keys())}"
            current = current[k]
    return current


@then('the response nested field "{path}" should equal "{value}"')
def step_nested_field_equals(context, path, value):
    """Assert a nested field, e.g. 'name_t9n.en' should equal 'Color' or 'warnings.0.code'."""
    current = _walk_nested(context.response_data, path)
    assert str(current) == value, f"Expected '{path}' = '{value}', got '{current}'"


@then('the response nested field "{path}" should not be null')
def step_nested_field_not_null(context, path):
    """Assert a nested field is present and non-null, e.g. 'ENT-C004.omnibus_gross'."""
    current = _walk_nested(context.response_data, path)
    assert current is not None, f"Expected '{path}' to not be null"


@then('the response nested field "{path}" should equal integer {value:d}')
def step_nested_field_equals_integer(context, path, value):
    """Integer-typed comparison for a nested field. Closes a gap where
    boolean/integer values flowed through ``should equal "False"`` style
    string matching (works but semantically lossy when the schema actually returns int).
    """
    current = _walk_nested(context.response_data, path)
    assert current == value, f"Expected '{path}' = {value} (int), got {current!r}"


@then('the response nested field "{path}" should be true')
def step_nested_field_is_true(context, path):
    current = _walk_nested(context.response_data, path)
    assert current is True, f"Expected '{path}' is True, got {current!r}"


@then('the response nested field "{path}" should be false')
def step_nested_field_is_false(context, path):
    current = _walk_nested(context.response_data, path)
    assert current is False, f"Expected '{path}' is False, got {current!r}"
