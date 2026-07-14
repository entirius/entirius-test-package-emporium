# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Cynthia-specific step definitions."""

from __future__ import annotations

from behave import then

from entirius_tests.assertions import extract_items
from entirius_tests.csv_loader import load_products


@then('the response data item should have SKU "{sku}"')
def step_response_data_item_has_sku(context, sku):
    data = context.response_data.get("data", context.response_data)
    if isinstance(data, list):
        found = any(item.get("sku") == sku for item in data)
        assert found, f"SKU {sku} not found in list response"
    else:
        actual = data.get("sku")
        assert actual == sku, f"Expected SKU '{sku}', got '{actual}'"


@then("the first CSV product SKU should exist in the API response")
def step_first_csv_product_exists(context):
    csv_data = load_products(context.test_package_path, context.channel)
    first_sku = csv_data[0]["sku"]
    items = extract_items(context.response)
    api_skus = {item.get("sku") for item in items}
    assert first_sku in api_skus, f"First CSV product SKU '{first_sku}' not found in API response"


@then("the last CSV product SKU should exist in the API response")
def step_last_csv_product_exists(context):
    csv_data = load_products(context.test_package_path, context.channel)
    last_sku = csv_data[-1]["sku"]
    items = extract_items(context.response)
    api_skus = {item.get("sku") for item in items}
    assert last_sku in api_skus, f"Last CSV product SKU '{last_sku}' not found in API response"


@then("the first CSV product detail should be accessible by url_key")
def step_first_csv_product_detail_by_url_key(context):
    csv_data = load_products(context.test_package_path, context.channel)
    url_key = csv_data[0].get("url_key en", csv_data[0].get("url_key", ""))
    sku = csv_data[0]["sku"]
    url = context.api.matrix_url(context.channel, f"products/{url_key}/")
    resp = context.api.get(url, params={"language": "en", "currency": "EUR"})
    assert resp.status_code == 200, f"GET {url} returned {resp.status_code}"
    data = resp.json().get("data", resp.json())
    actual_sku = data.get("sku", "")
    assert actual_sku == sku, f"Expected SKU '{sku}' for url_key '{url_key}', got '{actual_sku}'"
