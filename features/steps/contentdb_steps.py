# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""ContentDB-specific steps for BDD testing."""

from __future__ import annotations

import requests
from behave import then, when

from entirius_tests.assertions import extract_items


@when('I GET the ContentDB endpoint "{path}"')
def step_get_contentdb(context, path):
    url = context.api.contentdb_url(path)
    context.response = context.api.get(url, params={"limit": 100})
    context.response_data = context.response.json()


@when('I GET the ContentDB published endpoint "{path}" with routes "{routes}"')
def step_get_contentdb_published_with_routes(context, path, routes):
    url = context.api.contentdb_url(f"published/{path}")
    context.response = context.api.get(url, params={"routes": routes, "language": "EN", "access_rights": 1})
    context.response_data = context.response.json()


@when('I GET the ContentDB published endpoint "{path}" with channel "{channel}"')
def step_get_contentdb_published_with_channel(context, path, channel):
    url = context.api.contentdb_url(f"published/{path}")
    context.response = context.api.get(url, params={"language": "EN", "channel": channel})
    context.response_data = context.response.json()


@when('I GET the ContentDB published endpoint "{path}"')
def step_get_contentdb_published(context, path):
    url = context.api.contentdb_url(f"published/{path}")
    context.response = context.api.get(url, params={"language": "EN", "access_rights": 1})
    context.response_data = context.response.json()


@then("the first item content should have sections_order")
def step_first_item_has_sections_order(context):
    items = extract_items(context.response)
    assert len(items) > 0, "Response is empty"
    content = items[0].get("content", {})
    assert "sections_order" in content, f"First item content missing 'sections_order'. Keys: {list(content.keys())}"
    assert len(content["sections_order"]) > 0, "sections_order is empty"


@then("the first item content should have tiles")
def step_first_item_has_tiles(context):
    items = extract_items(context.response)
    assert len(items) > 0, "Response is empty"
    content = items[0].get("content", {})
    assert "tiles" in content, f"First item content missing 'tiles'. Keys: {list(content.keys())}"
    assert len(content["tiles"]) > 0, "tiles is empty"


def _find_hero_tile(items):
    """Find the first tile with core_type 'tile-hero' across all items."""
    for item in items:
        content = item.get("content", {})
        tiles = content.get("tiles", {})
        for tile_id, tile in tiles.items():
            if tile.get("core_type") == "tile-hero":
                return tile
    return None


@then("the first hero tile should have images_set with desktop")
def step_hero_tile_has_images_set_desktop(context):
    items = extract_items(context.response)
    hero = _find_hero_tile(items)
    assert hero is not None, "No tile with core_type 'tile-hero' found"
    images_set = hero.get("images_set", {})
    assert images_set, f"Hero tile has no images_set. Keys: {list(hero.keys())}"
    assert "desktop" in images_set, f"images_set missing 'desktop'. Keys: {list(images_set.keys())}"


@then('the tiles should include core_type "{core_type}"')
def step_tiles_include_core_type(context, core_type):
    items = extract_items(context.response)
    found = False
    for item in items:
        content = item.get("content", {})
        tiles = content.get("tiles", {})
        for tile in tiles.values():
            if tile.get("core_type") == core_type:
                found = True
                break
        if found:
            break
    assert found, f"No tile with core_type '{core_type}' found"


@then("the first hero tile should have a dye value")
def step_hero_tile_has_dye(context):
    items = extract_items(context.response)
    hero = _find_hero_tile(items)
    assert hero is not None, "No tile with core_type 'tile-hero' found"
    assert "dye" in hero, f"Hero tile missing 'dye'. Keys: {list(hero.keys())}"
    assert isinstance(hero["dye"], int), f"Expected dye to be int, got {type(hero['dye']).__name__}: {hero['dye']}"


@then('the tiles should include a tile with product_sku "{sku}"')
def step_tiles_include_product_sku(context, sku):
    items = extract_items(context.response)
    found = False
    for item in items:
        content = item.get("content", {})
        tiles = content.get("tiles", {})
        for tile in tiles.values():
            if tile.get("product_sku") == sku:
                found = True
                break
        if found:
            break
    assert found, f"No tile with product_sku '{sku}' found"


@then("at least one item should have extension images_set")
def step_at_least_one_item_extension_images_set(context):
    items = extract_items(context.response)
    assert len(items) > 0, "Response is empty"
    found = any("images_set" in item.get("extension", {}) for item in items)
    assert found, (
        "No item has extension.images_set. "
        f"Extension keys: {[list(item.get('extension', {}).keys()) for item in items]}"
    )


# --- Navigation steps ---


def _get_navigation_items(context) -> list:
    """Extract items list from navigation content."""
    data = context.response_data
    content = data.get("content", {})
    assert isinstance(content, dict), f"Expected 'content' to be a dict, got {type(content).__name__}"
    items = content.get("items", [])
    assert isinstance(items, list), f"Expected 'content.items' to be a list, got {type(items).__name__}"
    return items


@then("the navigation content should have items")
def step_navigation_has_items(context):
    items = _get_navigation_items(context)
    assert len(items) > 0, "Navigation content.items is empty"


@then("the navigation content should have {count:d} items")
def step_navigation_item_count(context, count):
    items = _get_navigation_items(context)
    assert len(items) == count, f"Expected {count} navigation items, got {len(items)}"


@then('the navigation items should include display_as "{display_as}"')
def step_navigation_includes_display_as(context, display_as):
    items = _get_navigation_items(context)
    found = any(item.get("display_as") == display_as for item in items)
    assert found, (
        f"No navigation item with display_as='{display_as}'. Values: {[item.get('display_as') for item in items]}"
    )


@then('the first navigation item should have label "{label}"')
def step_first_navigation_item_label(context, label):
    items = _get_navigation_items(context)
    assert len(items) > 0, "Navigation content.items is empty"
    actual = items[0].get("label")
    assert actual == label, f"Expected first item label '{label}', got '{actual}'"


@then('the first navigation item should have display_as "{display_as}"')
def step_first_navigation_item_display_as(context, display_as):
    items = _get_navigation_items(context)
    assert len(items) > 0, "Navigation content.items is empty"
    actual = items[0].get("display_as")
    assert actual == display_as, f"Expected first item display_as '{display_as}', got '{actual}'"


@then('the navigation item with label "{label}" should have display_as "{display_as}"')
def step_navigation_item_by_label_display_as(context, label, display_as):
    items = _get_navigation_items(context)
    matching = [item for item in items if item.get("label") == label]
    assert matching, f"No navigation item with label '{label}'. Labels: {[item.get('label') for item in items]}"
    actual = matching[0].get("display_as")
    assert actual == display_as, f"Expected item '{label}' display_as '{display_as}', got '{actual}'"


@then("the first navigation item should have columns")
def step_first_navigation_item_has_columns(context):
    items = _get_navigation_items(context)
    assert len(items) > 0, "Navigation content.items is empty"
    columns = items[0].get("columns", [])
    assert isinstance(columns, list), f"Expected 'columns' to be a list, got {type(columns).__name__}"
    assert len(columns) > 0, "First navigation item has no columns"


@then("the first navigation item should have {count:d} columns")
def step_first_navigation_item_column_count(context, count):
    items = _get_navigation_items(context)
    assert len(items) > 0, "Navigation content.items is empty"
    columns = items[0].get("columns", [])
    assert len(columns) == count, f"Expected {count} columns in first navigation item, got {len(columns)}"


@then('the first column of the first navigation item should have heading "{heading}"')
def step_first_column_heading(context, heading):
    items = _get_navigation_items(context)
    assert len(items) > 0, "Navigation content.items is empty"
    columns = items[0].get("columns", [])
    assert len(columns) > 0, "First navigation item has no columns"
    actual = columns[0].get("heading")
    assert actual == heading, f"Expected first column heading '{heading}', got '{actual}'"


# --- Admin v1 requests + error body assertions ---


def _store_body(context):
    try:
        context.response_data = context.response.json()
    except Exception:
        context.response_data = {}


@when('I GET the ContentDB admin endpoint "{path}"')
def step_get_contentdb_admin(context, path):
    context.response = context.api.get(context.api.contentdb_admin_url(path), params={"limit": 100})
    _store_body(context)


@when('I GET the ContentDB admin endpoint "{path}" without auth')
def step_get_contentdb_admin_no_auth(context, path):
    # Bypass the session client so the Background's Authorization header is not sent.
    context.response = requests.get(context.api.contentdb_admin_url(path), timeout=30)
    _store_body(context)


@when('I DELETE the ContentDB admin endpoint "{path}"')
def step_delete_contentdb_admin(context, path):
    context.response = context.api.delete(context.api.contentdb_admin_url(path))
    if context.response.status_code == 204:
        context.response_data = {}
    else:
        _store_body(context)


@when('I DELETE the ContentDB admin endpoint "{path}" without auth')
def step_delete_contentdb_admin_no_auth(context, path):
    context.response = requests.delete(context.api.contentdb_admin_url(path), timeout=30)
    _store_body(context)


@then('the response data list should contain "{text}"')
def step_response_data_list_contains(context, text):
    payload = (context.response_data or {}).get("data")
    assert isinstance(payload, list) and payload, f"Expected non-empty data list, got: {context.response_data}"
    joined = " | ".join(str(item) for item in payload)
    assert text in joined, f"Expected '{text}' in data list, got: {payload}"
