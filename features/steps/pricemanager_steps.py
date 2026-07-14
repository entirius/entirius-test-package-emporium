# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Price verification step definitions."""

from __future__ import annotations

from behave import given, then

from entirius_tests.assertions import extract_items
from entirius_tests.csv_loader import load_pricelist, load_products


@given('the CSV pricelist is loaded for channel "{channel}"')
def step_load_csv_pricelist(context, channel):
    context.csv_data = load_pricelist(context.test_package_path, channel)


@then("matrix products should have final_price values")
def step_matrix_products_have_prices(context):
    items = extract_items(context.response)
    assert len(items) > 0, "No products in API response"
    products_with_prices = sum(1 for item in items if item.get("final_price") is not None)
    assert products_with_prices > 0, (
        f"No products have final_price. Sample item keys: {list(items[0].keys()) if items else 'none'}"
    )


@then("the CSV pricelist should contain {count:d} entries")
def step_csv_pricelist_count(context, count):
    assert len(context.csv_data) == count, f"Expected {count} pricelist entries, got {len(context.csv_data)}"


@then("the CSV should have products with special prices")
def step_csv_has_special_prices(context):
    specials = [row for row in context.csv_data if row.get("special_price_gross", "").strip()]
    assert len(specials) > 0, "No products with special prices in CSV"


@then("the CSV pricelist count should match the CSV product count")
def step_pricelist_matches_products(context):
    products = load_products(context.test_package_path, context.primary_channel)
    assert len(context.csv_data) == len(products), (
        f"Pricelist has {len(context.csv_data)} entries, but CSV products has {len(products)}"
    )
