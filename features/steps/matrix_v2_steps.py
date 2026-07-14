# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Matrix v2 step definitions — response shape and value assertions for storefront API.

Relies on existing steps from pim_advanced_steps.py:
  - @when('I GET "{path}"')
  - @then('the response status is {status:d}')
  - @then('the response field "{field}" is true')
  - @then('the response field "{field}" is not null')

And from admin_crud_steps.py:
  - @then('the response field "{field}" should equal "{value}"')

This file adds Matrix v2-specific assertions not covered elsewhere.
"""

from behave import given, then

# ── Given steps ──────────────────────────────────────────────────────


@given("the API base URL is configured")
def step_api_base_configured(context):
    assert context.api is not None, "API client not configured"


@given('channel "{channel}" exists with products')
def step_channel_exists(context, channel):
    context.channel = channel


# ── Response key assertions ──────────────────────────────────────────


@then('the response has key "{key}"')
def step_response_has_key(context, key):
    data = context.response_data
    assert key in data, f"Missing key '{key}'. Keys: {list(data.keys())}"


@then("the response is a dict")
def step_response_is_dict(context):
    assert isinstance(context.response_data, dict)


@then("the response is a list")
def step_response_is_list(context):
    assert isinstance(context.response_data, list)


@then("the response is empty dict")
def step_response_is_empty_dict(context):
    assert context.response_data == {}


@then('"{key}" is a list')
def step_key_is_list(context, key):
    val = _resolve_dotted(context.response_data, key)
    assert isinstance(val, list), f"Expected '{key}' to be list, got {type(val)}"


@then('"{key}" has exactly {count:d} item')
@then('"{key}" has exactly {count:d} items')
def step_key_has_count(context, key, count):
    val = _resolve_dotted(context.response_data, key)
    assert len(val) == count, f"Expected {count} items in '{key}', got {len(val)}"


@then('"{key}" is false')
def step_key_is_false(context, key):
    val = _resolve_dotted(context.response_data, key)
    assert val is False, f"Expected '{key}' to be false, got {val}"


@then('"{key}" is at most {n:d}')
def step_key_at_most(context, key, n):
    val = _resolve_dotted(context.response_data, key)
    assert val <= n, f"Expected '{key}' <= {n}, got {val}"


@then('"{key}" has key "{subkey}"')
def step_nested_has_key(context, key, subkey):
    obj = _resolve_dotted(context.response_data, key)
    assert isinstance(obj, dict), f"'{key}' is not a dict"
    assert subkey in obj, f"Missing '{subkey}' in '{key}'. Keys: {list(obj.keys())}"


@then('"{dotted}" is {value:d}')
def step_dotted_is_int(context, dotted, value):
    val = _resolve_dotted(context.response_data, dotted)
    assert val == value, f"Expected '{dotted}' = {value}, got {val}"


@then('the response header "{header}" is "{value}"')
def step_response_header(context, header, value):
    actual = context.response.headers.get(header)
    assert actual == value, f"Header '{header}': expected '{value}', got '{actual}'"


# ── First result assertions ──────────────────────────────────────────


def _first_result(context):
    results = context.response_data.get("results", [])
    assert results, "No results in response"
    return results[0]


@then('the first result has key "{key}"')
def step_first_result_has_key(context, key):
    r = _first_result(context)
    assert key in r, f"First result missing '{key}'. Keys: {list(r.keys())}"


@then('the first result does not have key "{key}"')
def step_first_result_no_key(context, key):
    r = _first_result(context)
    assert key not in r, f"First result should not have '{key}'"


@then('the first result price has key "{key}"')
def step_first_result_price_has_key(context, key):
    r = _first_result(context)
    price = r.get("price", {})
    assert price, "First result has no price object"
    assert key in price, f"Price missing '{key}'. Keys: {list(price.keys())}"


@then('the first result field "{field}" equals "{value}"')
def step_first_result_field_equals(context, field, value):
    r = _first_result(context)
    actual = r.get(field)
    assert str(actual) == value, f"First result '{field}': expected '{value}', got '{actual}'"


@then('the first result field "{field}" is not empty')
def step_first_result_field_not_empty(context, field):
    r = _first_result(context)
    val = r.get(field)
    assert val, f"First result '{field}' is empty or null"


@then('the first result field "{field}" is a string')
def step_first_result_field_is_string(context, field):
    r = _first_result(context)
    assert isinstance(r.get(field), str), f"First result '{field}' is {type(r.get(field))}, expected str"


@then('the first result field "{field}" is a list')
def step_first_result_field_is_list(context, field):
    r = _first_result(context)
    assert isinstance(r.get(field), list), f"First result '{field}' is {type(r.get(field))}, expected list"


@then('the first result field "{field}" is a dict')
def step_first_result_field_is_dict(context, field):
    r = _first_result(context)
    assert isinstance(r.get(field), dict), f"First result '{field}' is {type(r.get(field))}, expected dict"


@then('the first result price field "{field}" equals "{value}"')
def step_first_result_price_field_equals(context, field, value):
    r = _first_result(context)
    price = r.get("price", {})
    actual = price.get(field)
    assert str(actual) == value, f"Price '{field}': expected '{value}', got '{actual}'"


@then('the first result price field "{field}" is an integer')
def step_first_result_price_field_is_int(context, field):
    r = _first_result(context)
    price = r.get("price", {})
    assert isinstance(price.get(field), int), f"Price '{field}' is {type(price.get(field))}, expected int"


@then("the first result has at least {count:d} attributes")
def step_first_result_attributes_count(context, count):
    r = _first_result(context)
    attrs = r.get("attributes", [])
    assert len(attrs) >= count, f"Expected >= {count} attributes, got {len(attrs)}"


# ── Helpers ──────────────────────────────────────────────────────────


def _resolve_dotted(data, dotted_key):
    """Resolve a dotted path like 'products.total' against a nested dict."""
    parts = dotted_key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            assert part in current, f"Key '{part}' not found in {list(current.keys())}"
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            raise AssertionError(f"Cannot resolve '{part}' in {type(current)}")
    return current
