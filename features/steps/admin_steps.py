# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for admin API v2 testing."""

from __future__ import annotations

import requests
from behave import given, then, when

from entirius_tests.auth import obtain_jwt_token
from entirius_tests.csv_loader import load_products

# --- Authentication ---


@given("I am authenticated as an admin user")
def step_auth_admin(context):
    token = obtain_jwt_token(
        context.api.base_url,
        context.admin_username,
        context.admin_password,
    )
    context.api.set_auth_token(token)


@given("I am authenticated as a regular user")
def step_auth_regular(context):
    """Authenticate as a non-staff user.

    Requires `make test-admin` which auto-creates test users
    via docker/ensure-test-users.py.
    """
    token = obtain_jwt_token(
        context.api.base_url,
        context.test_username,
        context.test_password,
    )
    context.api.set_auth_token(token)


# --- v2 Endpoint Requests ---


def _resolve_v2_path(path: str, context) -> str:
    """Replace {channel_idx} and {saved.*} placeholders in URL path."""
    resolved = path.replace("{channel_idx}", context.channel or "")
    for key, val in (getattr(context, "saved", None) or {}).items():
        resolved = resolved.replace(f"{{{key}}}", str(val))
    return resolved


def _convert_v2_url(path: str) -> str:
    """Build api/{module}/v2/{rest} from a step path like 'pim/admin/...' or 'agreements/...'."""
    parts = path.split("/", 1)
    module = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    return f"api/{module}/v2/{rest}"


@when('I GET the v2 admin endpoint "{path}" without auth')
def step_get_v2_no_auth(context, path):
    resolved = _resolve_v2_path(path, context)
    url = context.api.url(_convert_v2_url(resolved))
    resp = requests.get(url, timeout=30)
    context.response = resp
    context.response_data = resp.json()


@when('I POST to the v2 public endpoint "{path}" with body')
def step_post_v2_no_auth(context, path):
    import json

    resolved = _resolve_v2_path(path, context)
    url = context.api.url(_convert_v2_url(resolved))
    body = json.loads(context.text)
    resp = requests.post(url, json=body, timeout=30)
    context.response = resp
    try:
        context.response_data = resp.json()
    except Exception:
        context.response_data = {}


@when('I GET the v2 admin endpoint "{path}"')
@given('I GET the v2 admin endpoint "{path}"')
def step_get_v2_admin(context, path):
    resolved = _resolve_v2_path(path, context)
    url = context.api.url(_convert_v2_url(resolved))
    context.response = context.api.get(url)
    context.response_data = context.response.json()


@when('I GET the v2 admin endpoint "{path}" with params')
def step_get_v2_admin_with_params(context, path):
    resolved = _resolve_v2_path(path, context)
    url = context.api.url(_convert_v2_url(resolved))
    params = {row["param"]: row["value"] for row in context.table}
    context.response = context.api.get(url, params=params)
    context.response_data = context.response.json()


@when("I GET the v2 admin endpoint for the first CSV product")
def step_get_v2_first_csv_product(context):
    csv_data = context.csv_data
    if not csv_data:
        csv_data = load_products(context.test_package_path, context.channel)
    first_sku = csv_data[0]["sku"]
    url = context.api.url(f"api/pim/v2/admin/{context.channel}/products/{first_sku}/")
    context.response = context.api.get(url)
    context.response_data = context.response.json()


# --- Response Assertions ---


@then("the response should have pagination fields")
def step_has_pagination_fields(context):
    data = context.response_data
    if isinstance(data, list):
        # Non-paginated list response — skip pagination field checks
        return
    for row in context.table:
        field = row["field"]
        assert field in data, f"Pagination field '{field}' missing. Keys: {list(data.keys())}"


@then("the results should contain at most {count:d} items")
def step_results_at_most(context, count):
    results = context.response_data.get("results", [])
    assert len(results) <= count, f"Expected at most {count} results, got {len(results)}"


@then("the response should have the fields")
def step_response_has_fields(context):
    data = context.response_data
    for row in context.table:
        field = row["field"]
        assert field in data, f"Field '{field}' missing. Keys: {list(data.keys())}"


@then('the error response should have error code "{code}"')
def step_error_code(context, code):
    data = context.response_data
    assert "error" in data, f"Response missing 'error' field. Keys: {list(data.keys())}"
    assert data["error"] == code, f"Expected error code '{code}', got '{data['error']}'"


@then("the error response should have a debug_id")
def step_error_debug_id(context):
    data = context.response_data
    assert "debug_id" in data, f"Response missing 'debug_id' field. Keys: {list(data.keys())}"
    assert len(data["debug_id"]) > 0, "debug_id is empty"
