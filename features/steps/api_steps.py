# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""HTTP verb steps for API testing."""

from __future__ import annotations

from behave import given, then, when

from entirius_tests.assertions import assert_status, extract_items
from entirius_tests.csv_loader import load_products


@when('I GET the Cynthia endpoint "{path}"')
def step_get_cynthia(context, path):
    url = context.api.cynthia_url(context.channel, path)
    context.response = context.api.get(url, params={"limit": 100})
    context.response_data = context.response.json()


@when('I GET the Cynthia endpoint "{path}" with params')
def step_get_cynthia_with_params(context, path):
    url = context.api.cynthia_url(context.channel, path)
    params = {"limit": 100}
    for row in context.table:
        params[row["param"]] = row["value"]
    context.response = context.api.get(url, params=params)
    context.response_data = context.response.json()


@when('I GET the Cynthia detail "{path}"')
def step_get_cynthia_detail(context, path):
    url = context.api.cynthia_url(context.channel, path)
    context.response = context.api.get(url)
    context.response_data = context.response.json()


@when('I GET the Matrix endpoint "{path}"')
def step_get_matrix(context, path):
    url = context.api.matrix_url(context.channel, path)
    context.response = context.api.get(url, params={"limit": 100, "language": "en", "currency": "EUR"})
    context.response_data = context.response.json()


@when('I GET the Matrix endpoint "{path}" with params')
def step_get_matrix_with_params(context, path):
    url = context.api.matrix_url(context.channel, path)
    params = {"limit": 100, "language": "en", "currency": "EUR"}
    for row in context.table:
        params[row["param"]] = row["value"]
    context.response = context.api.get(url, params=params)
    context.response_data = context.response.json()


@then("the response status should be {status:d}")
def step_response_status(context, status):
    assert_status(context.response, status)


@then("the response should contain {count:d} items")
def step_response_count(context, count):
    items = extract_items(context.response)
    assert len(items) == count, f"Expected {count} items, got {len(items)}"


@then("the response should contain at least {count:d} items")
def step_response_at_least_count(context, count):
    items = extract_items(context.response)
    assert len(items) >= count, f"Expected at least {count} items, got {len(items)}"


@then("the response count should match CSV product count")
def step_count_matches_csv(context):
    items = extract_items(context.response)
    csv_data = load_products(context.test_package_path, context.channel)
    assert len(items) == len(csv_data), f"Expected {len(csv_data)} items (from CSV), got {len(items)}"


@given("for each configured channel the CSV products are verified against the API")
def step_verify_all_channels_products(context):
    for channel in context.channels:
        csv_data = load_products(context.test_package_path, channel)
        url = context.api.matrix_url(channel, "products/")
        resp = context.api.get(url, params={"limit": 100, "language": "en", "currency": "EUR"})
        assert_status(resp, 200)
        items = extract_items(resp)
        api_skus = {item.get("sku") for item in items}
        for row in csv_data:
            assert row["sku"] in api_skus, f"[{channel}] SKU {row['sku']} not in API response"
