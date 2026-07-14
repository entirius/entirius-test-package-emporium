# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CSV-driven import verification steps."""

from __future__ import annotations

from behave import given, then

from entirius_tests.assertions import extract_items
from entirius_tests.csv_loader import (
    load_attributes,
    load_categories,
    load_feature_sets,
    load_products,
)


@given('the CSV categories are loaded for channel "{channel}"')
def step_load_csv_categories(context, channel):
    context.csv_data = load_categories(context.test_package_path, channel)


@given('the CSV products are loaded for channel "{channel}"')
def step_load_csv_products(context, channel):
    context.csv_data = load_products(context.test_package_path, channel)


@given('the CSV attributes are loaded for type "{attr_type}"')
def step_load_csv_attributes(context, attr_type):
    context.csv_data = load_attributes(context.test_package_path, attr_type)
    context.attr_type = attr_type


@then("every CSV leaf category should exist in the API response")
def step_every_csv_leaf_category_in_api(context):
    items = extract_items(context.response)
    api_idxs = {item.get("idx", "") for item in items}
    # Skip root -- Cynthia API excludes the root category
    leaf_categories = [row for row in context.csv_data if row["idx"] != "root"]
    for row in leaf_categories:
        csv_idx = row["idx"]
        assert csv_idx in api_idxs, f"CSV category '{csv_idx}' not found in API. API categories: {sorted(api_idxs)}"


@then("the API category count should be at least the CSV leaf count")
def step_api_category_count_gte_csv_leaf(context):
    items = extract_items(context.response)
    leaf_count = sum(1 for row in context.csv_data if row["idx"] != "root")
    api_count = len(items)
    assert api_count >= leaf_count, f"API has {api_count} categories, CSV has {leaf_count} leaf categories"


@then("every CSV product SKU should exist in the API response")
def step_every_csv_product_in_api(context):
    items = extract_items(context.response)
    api_skus = {item.get("sku", "") for item in items}
    for row in context.csv_data:
        csv_sku = row["sku"]
        assert csv_sku in api_skus, f"CSV product '{csv_sku}' not found in API. API has {len(api_skus)} products"


@then("the API product count should be at least the CSV count")
def step_api_product_count_gte_csv(context):
    items = extract_items(context.response)
    csv_count = len(context.csv_data)
    api_count = len(items)
    assert api_count >= csv_count, f"API has {api_count} products, CSV has {csv_count}"


@then("each CSV product name should match the API response")
def step_csv_product_names_match_api(context):
    items = extract_items(context.response)
    api_by_sku = {item["sku"]: item for item in items if "sku" in item}
    for row in context.csv_data:
        sku = row["sku"]
        expected_name = row.get("name en", "")
        if sku in api_by_sku:
            api_name = api_by_sku[sku].get("name", "")
            assert expected_name in api_name or api_name == expected_name, (
                f"Product {sku}: expected name containing '{expected_name}', got '{api_name}'"
            )


@then("products with badges should reference valid badge values")
def step_products_with_badges_valid(context):
    csv_badges = {row["idx"] for row in context.csv_data}
    items = extract_items(context.response)
    for item in items:
        badges = item.get("badges") or []
        for badge in badges:
            badge_idx = badge.get("idx", badge) if isinstance(badge, dict) else badge
            if badge_idx:
                assert badge_idx in csv_badges, f"Product badge '{badge_idx}' not in CSV badges: {csv_badges}"


@then("products with series should reference valid series values")
def step_products_with_series_valid(context):
    csv_series = {row["idx"] for row in context.csv_data}
    items = extract_items(context.response)
    for item in items:
        series = item.get("series")
        if isinstance(series, dict):
            series = series.get("idx", "")
        if series and series != "":
            assert series in csv_series, f"Product series '{series}' not in CSV series: {csv_series}"


@then("the CSV should contain {count:d} {attr_type} values")
def step_csv_attribute_count(context, count, attr_type):
    assert len(context.csv_data) == count, f"Expected {count} {attr_type} values, got {len(context.csv_data)}"


@then("the CSV attributes should be non-empty")
def step_csv_attributes_non_empty(context):
    assert len(context.csv_data) > 0, f"Expected non-empty CSV for {context.attr_type}, got 0 rows"


@then('the CSV should contain "{product_type}" products')
def step_csv_contains_product_type(context, product_type):
    counts = context.product_type_counts
    assert counts.get(product_type, 0) > 0, f"Expected CSV to contain '{product_type}' products, got counts: {counts}"


@then('the CSV should contain {count:d} "{product_type}" products')
def step_csv_product_type_count(context, count, product_type):
    counts = context.product_type_counts
    actual = counts.get(product_type, 0)
    assert actual == count, f"Expected {count} '{product_type}' products, got {actual}. All counts: {counts}"


@then("the total CSV product count should be {count:d}")
def step_csv_total_product_count(context, count):
    counts = context.product_type_counts
    total = sum(counts.values())
    assert total == count, f"Expected {count} total products, got {total}. Counts: {counts}"


# --- Feature Sets ---


@given("the CSV feature sets are loaded")
def step_load_csv_feature_sets(context):
    context.csv_feature_sets = load_feature_sets(context.test_package_path)


@then("the feature sets should include {idxs_str}")
def step_feature_sets_include(context, idxs_str):
    csv_idxs = {row["idx"] for row in context.csv_feature_sets}
    expected = [s.strip().strip('"') for s in idxs_str.split(",")]
    for idx in expected:
        assert idx in csv_idxs, f"Feature set '{idx}' not in CSV. Found: {sorted(csv_idxs)}"


@then("the feature set count should match CSV")
def step_feature_set_count_matches(context):
    count = len(context.csv_feature_sets)
    assert count > 0, "No feature sets in CSV"
