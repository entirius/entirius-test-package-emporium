# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Quantity / stock verification step definitions."""

from __future__ import annotations

from behave import then

from entirius_tests.csv_loader import load_products


@then("the CSV quantities should contain {count:d} entries")
def step_csv_quantities_count(context, count):
    assert len(context.csv_data) == count, f"Expected {count} quantity entries, got {len(context.csv_data)}"


@then("the CSV should have products with zero quantity")
def step_csv_has_zero_qty(context):
    zero_qty = [row for row in context.csv_data if int(row["quantity"]) == 0]
    assert len(zero_qty) > 0, "No products with zero quantity in CSV"


@then("the CSV should have products with positive quantity")
def step_csv_has_positive_qty(context):
    positive = [row for row in context.csv_data if int(row["quantity"]) > 0]
    assert len(positive) > 0, "No products with positive quantity in CSV"


@then("the following SKUs should have zero quantity")
def step_skus_have_zero_qty(context):
    qty_by_sku = {row["sku"]: int(row["quantity"]) for row in context.csv_data}
    for row in context.table:
        sku = row["sku"]
        assert sku in qty_by_sku, f"SKU {sku} not found in CSV quantities"
        assert qty_by_sku[sku] == 0, f"SKU {sku} expected qty 0, got {qty_by_sku[sku]}"


@then("all zero-quantity SKUs from CSV should be confirmed")
def step_zero_qty_from_csv(context):
    zero_skus = [row for row in context.csv_data if int(row["quantity"]) == 0]
    assert len(zero_skus) > 0, "No zero-quantity products in CSV"
    qty_by_sku = {row["sku"]: int(row["quantity"]) for row in context.csv_data}
    for row in zero_skus:
        assert qty_by_sku[row["sku"]] == 0, f"SKU {row['sku']} expected qty 0, got {qty_by_sku[row['sku']]}"


@then("the CSV quantities count should match the CSV product count")
def step_qty_matches_products(context):
    products = load_products(context.test_package_path, context.primary_channel)
    assert len(context.csv_data) == len(products), (
        f"Quantities has {len(context.csv_data)} entries, but CSV products has {len(products)}"
    )
