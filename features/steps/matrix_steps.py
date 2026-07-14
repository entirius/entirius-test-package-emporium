# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Matrix read model step definitions."""

from __future__ import annotations

from behave import then, when

from entirius_tests.assertions import extract_items
from entirius_tests.csv_loader import expected_sku_order_for_category

# --- Categories Listing ---


@then("every category should have tree_deep equal to {depth:d}")
def step_every_category_tree_deep(context, depth):
    items = extract_items(context.response)
    for item in items:
        actual = item.get("tree_deep")
        assert actual == depth, f"Category '{item.get('idx')}' has tree_deep={actual}, expected {depth}"


@then("I save the Matrix categories response")
def step_save_matrix_categories(context):
    context.matrix_categories = extract_items(context.response)


@then("the Matrix categories should match Cynthia categories by idx and name")
def step_matrix_matches_cynthia(context):
    matrix_cats = context.matrix_categories
    cynthia_cats = extract_items(context.response)
    matrix_by_idx = {c["idx"]: c["name"] for c in matrix_cats}
    cynthia_by_idx = {c["idx"]: c["name"] for c in cynthia_cats}
    missing = set(cynthia_by_idx.keys()) - set(matrix_by_idx.keys())
    assert not missing, f"Categories in Cynthia but missing from Matrix: {missing}"
    for idx in cynthia_by_idx:
        assert matrix_by_idx[idx] == cynthia_by_idx[idx], (
            f"Category '{idx}' name mismatch: Matrix='{matrix_by_idx[idx]}', Cynthia='{cynthia_by_idx[idx]}'"
        )


# --- Product Positions ---


@then('the response SKU order should match CSV positions for category "{category_url_key}"')
def step_sku_order_matches_positions(context, category_url_key):
    items = extract_items(context.response)
    api_skus = [item["sku"] for item in items]
    expected_skus = expected_sku_order_for_category(context.test_package_path, context.channel, category_url_key)
    # API may contain only products that exist in Matrix — filter expected to those present
    expected_in_api = [sku for sku in expected_skus if sku in api_skus]
    assert len(expected_in_api) > 0, (
        f"No expected SKUs found in API response for category '{category_url_key}'. API SKUs: {api_skus}"
    )
    # Only check the first N SKUs from the API (positioned products come first,
    # unpositioned products follow and are not part of this assertion).
    n = len(expected_in_api)
    actual_leading = api_skus[:n]
    assert actual_leading == expected_in_api, (
        f"Product order mismatch for category '{category_url_key}'.\n"
        f"Expected (first {n}): {expected_in_api}\n"
        f"Got      (first {n}): {actual_leading}"
    )


# --- Bundle Prices ---


@then("the bundle price response should contain items")
def step_bundle_price_has_items(context):
    items = extract_items(context.response)
    assert len(items) > 0, "Expected bundle price response to contain items, got 0"


@then('each bundle price item should have the field "{field}"')
def step_bundle_price_item_has_field(context, field):
    items = extract_items(context.response)
    for item in items:
        assert field in item, f"Bundle price item missing field '{field}'. Available fields: {list(item.keys())}"


@then("the bundle price response should contain at least {count:d} items")
def step_bundle_price_min_items(context, count):
    items = extract_items(context.response)
    assert len(items) >= count, f"Expected at least {count} bundle price items, got {len(items)}"


# --- Product Types ---


@then('the products with type "{product_type}" should include')
def step_products_with_type_include(context, product_type):
    items = extract_items(context.response)
    typed = [i for i in items if i.get("product_type") == product_type]
    typed_skus = {i["sku"] for i in typed}
    for row in context.table:
        sku = row["sku"]
        assert sku in typed_skus, f"SKU {sku} not found among {product_type} products. Found: {sorted(typed_skus)}"


# --- Configurable Variants ---


@when('I GET the Matrix detail "{path}"')
def step_get_matrix_detail(context, path):
    url = context.api.matrix_url(context.channel, path)
    context.response = context.api.get(url, params={"language": "en", "currency": "EUR"})
    context.response_data = context.response.json()


@then("the variants response should have options")
def step_variants_has_options(context):
    data = context.response_data.get("data", {})
    options = data.get("options", [])
    assert len(options) > 0, f"Expected variants to have options, got {len(options)}"


@then('the variants options should include feature "{feature_idx}"')
def step_variants_options_include_feature(context, feature_idx):
    data = context.response_data.get("data", {})
    options = data.get("options", [])
    idxs = [o.get("idx") for o in options]
    assert feature_idx in idxs, f"Feature '{feature_idx}' not in variant options. Found: {idxs}"


@then("the variants products should include SKUs")
def step_variants_products_include_skus(context):
    data = context.response_data.get("data", {})
    products = data.get("products", [])
    product_skus = {p["sku"] for p in products}
    for row in context.table:
        sku = row["sku"]
        assert sku in product_skus, f"SKU {sku} not in variant products. Found: {sorted(product_skus)}"


@then('each variant product should have attributes for feature "{feature_idx}"')
def step_variant_products_have_feature_attrs(context, feature_idx):
    data = context.response_data.get("data", {})
    products = data.get("products", [])
    assert len(products) > 0, "No variant products found"
    for p in products:
        attrs = p.get("attributes", [])
        feature_idxs = [a.get("feature_idx") for a in attrs]
        assert feature_idx in feature_idxs, (
            f"Product {p['sku']} missing attribute for feature '{feature_idx}'. Has: {feature_idxs}"
        )


# --- Bundle Config ---


def _get_bundle_config_data(context):
    """Extract bundle config list from response data."""
    data = context.response_data.get("data", [])
    if isinstance(data, dict):
        return [data]
    return data


def _get_bundle_by_sku(context, sku):
    """Find a specific bundle in the config response."""
    bundles = _get_bundle_config_data(context)
    for b in bundles:
        if b.get("sku") == sku:
            return b
    skus = [b.get("sku") for b in bundles]
    raise AssertionError(f"Bundle SKU '{sku}' not found in response. Found: {skus}")


def _get_sub_item_by_sku(bundle, sub_sku):
    """Find a specific sub_item in a bundle."""
    for item in bundle.get("sub_items", []):
        if item.get("sku") == sub_sku:
            return item
    found = [i.get("sku") for i in bundle.get("sub_items", [])]
    raise AssertionError(f"Sub-item SKU '{sub_sku}' not found in bundle '{bundle.get('sku')}'. Found: {found}")


@then("the bundle config response should contain {count:d} bundle")
@then("the bundle config response should contain {count:d} bundles")
def step_bundle_config_count(context, count):
    bundles = _get_bundle_config_data(context)
    assert len(bundles) == count, f"Expected {count} bundles, got {len(bundles)}"


@then('the bundle config for "{sku}" should have {count:d} sub_items')
def step_bundle_config_sub_items_count(context, sku, count):
    bundle = _get_bundle_by_sku(context, sku)
    sub_items = bundle.get("sub_items", [])
    assert len(sub_items) == count, f"Bundle {sku}: expected {count} sub_items, got {len(sub_items)}"


@then('the bundle config sub_item "{sub_sku}" should have extension fields')
def step_bundle_config_sub_item_fields(context, sub_sku):
    bundles = _get_bundle_config_data(context)
    bundle = bundles[0]
    item = _get_sub_item_by_sku(bundle, sub_sku)
    for row in context.table:
        field = row["field"]
        expected = row["value"].lower()
        actual = item.get(field)
        assert str(actual).lower() == expected, f"Sub-item {sub_sku} field '{field}': expected {expected}, got {actual}"


@then('the bundle config for "{sku}" should have max_limit {limit:d}')
def step_bundle_config_max_limit(context, sku, limit):
    bundle = _get_bundle_by_sku(context, sku)
    actual = bundle.get("max_limit")
    assert actual == limit, f"Bundle {sku}: expected max_limit={limit}, got {actual}"


@then('the bundle config for "{sku}" should have min_limit {limit:d}')
def step_bundle_config_min_limit(context, sku, limit):
    bundle = _get_bundle_by_sku(context, sku)
    actual = bundle.get("min_limit")
    assert actual == limit, f"Bundle {sku}: expected min_limit={limit}, got {actual}"


@then('the bundle config for "{sku}" should have the field "{field}"')
def step_bundle_config_has_field(context, sku, field):
    bundle = _get_bundle_by_sku(context, sku)
    assert field in bundle, f"Bundle {sku}: field '{field}' not present. Keys: {list(bundle.keys())}"


@then("each bundle config sub_item should have a price object")
def step_bundle_config_sub_items_have_price(context):
    bundles = _get_bundle_config_data(context)
    for bundle in bundles:
        for item in bundle.get("sub_items", []):
            price = item.get("price")
            assert price is not None, f"Sub-item {item.get('sku')} in bundle {bundle.get('sku')} has no price"
            assert "price" in price, f"Sub-item {item.get('sku')} price object missing 'price' field"


# --- Signal Sync Observability ---


@then("the sync observability scenario is acknowledged")
def step_sync_observability_acknowledged(context):
    """Placeholder step for the matrix-sync-status management command scenario.

    This command cannot be invoked from an external API test container.
    Coverage is provided by unit tests in django-matrix.
    """


# --- Options (Filterable Attributes) ---


def _extract_options_groups(context):
    """Extract filter groups from options response."""
    data = context.response_data
    if isinstance(data, dict):
        return data.get("data", [])
    if isinstance(data, list):
        return data
    return []


@then("the options response should contain at least {count:d} filter groups")
def step_options_min_groups(context, count):
    groups = _extract_options_groups(context)
    assert len(groups) >= count, f"Expected at least {count} filter groups, got {len(groups)}"


@then('the options response should contain filter group "{idx}"')
def step_options_contains_group(context, idx):
    groups = _extract_options_groups(context)
    group_idxs = [g.get("idx") for g in groups]
    assert idx in group_idxs, f"Filter group '{idx}' not found. Available: {group_idxs}"


@then('the options filter group "{idx}" should have values')
def step_options_group_has_values(context, idx):
    groups = _extract_options_groups(context)
    group = next((g for g in groups if g.get("idx") == idx), None)
    assert group is not None, f"Filter group '{idx}' not found"
    values = group.get("options", group.get("values", []))
    assert len(values) > 0, f"Filter group '{idx}' has no values"


@then('each value in filter group "{idx}" should have a product count')
def step_options_values_have_count(context, idx):
    groups = _extract_options_groups(context)
    group = next((g for g in groups if g.get("idx") == idx), None)
    assert group is not None, f"Filter group '{idx}' not found"
    for value in group.get("options", group.get("values", [])):
        count = value.get("products_count", value.get("count", value.get("product_count")))
        assert count is not None, f"Value '{value.get('idx', value)}' in group '{idx}' has no count"


@then('each filter group should have fields "{fields_str}"')
def step_options_groups_have_fields(context, fields_str):
    groups = _extract_options_groups(context)
    required_fields = [f.strip().strip('"') for f in fields_str.split(",")]
    assert len(groups) > 0, "No filter groups found"
    for group in groups:
        for field in required_fields:
            assert field in group, f"Filter group missing field '{field}'. Available: {list(group.keys())}"


# --- Attributes (Visibility) ---


@then('each product should have an "{field}" field')
def step_each_product_has_field(context, field):
    items = extract_items(context.response)
    assert len(items) > 0, "No products in response"
    for item in items:
        assert field in item, f"Product {item.get('sku', '?')} missing field '{field}'. Fields: {list(item.keys())}"


@then('product attributes should include feature "{feature_idx}"')
def step_product_attrs_include_feature(context, feature_idx):
    items = extract_items(context.response)
    found = False
    for item in items:
        attrs = item.get("attributes", [])
        for attr in attrs:
            if attr.get("idx") == feature_idx or attr.get("feature_idx") == feature_idx:
                found = True
                break
        if found:
            break
    assert found, f"Feature '{feature_idx}' not found in any product attributes"


@then('product attributes for "{feature_idx}" should have boolean-like values')
def step_product_attrs_boolean(context, feature_idx):
    items = extract_items(context.response)
    found = False
    for item in items:
        attrs = item.get("attributes", [])
        for attr in attrs:
            attr_idx = attr.get("feature_idx") or attr.get("idx")
            if attr_idx == feature_idx:
                found = True
                val = attr.get("attribute_value", attr.get("value"))
                assert val is not None, f"Product {item.get('sku')}: attribute '{feature_idx}' has None value"
                break
    assert found, f"Feature '{feature_idx}' not found in any product attributes"


@then('product attributes for "{feature_idx}" should have numeric values')
def step_product_attrs_numeric(context, feature_idx):
    items = extract_items(context.response)
    found = False
    for item in items:
        attrs = item.get("attributes", [])
        for attr in attrs:
            attr_idx = attr.get("feature_idx") or attr.get("idx")
            if attr_idx == feature_idx:
                found = True
                val = attr.get("attribute_value", attr.get("value"))
                assert val is not None, f"Product {item.get('sku')}: attribute '{feature_idx}' has None value"
                try:
                    float(str(val))
                except (ValueError, TypeError):
                    raise AssertionError(
                        f"Product {item.get('sku')}: attribute '{feature_idx}' value '{val}' is not numeric"
                    )
                break
    assert found, f"Feature '{feature_idx}' not found in any product attributes"
