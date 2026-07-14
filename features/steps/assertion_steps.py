# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Assertion steps for verifying response content."""

from __future__ import annotations

from behave import then

from entirius_tests.assertions import extract_items


@then('each item should have the field "{field}"')
def step_each_item_has_field(context, field):
    items = extract_items(context.response)
    for i, item in enumerate(items):
        assert field in item, f"Item {i} missing field '{field}'. Keys: {list(item.keys())}"


@then("each item should have the fields")
def step_each_item_has_fields(context):
    items = extract_items(context.response)
    fields = [row["field"] for row in context.table]
    for i, item in enumerate(items):
        for field in fields:
            assert field in item, f"Item {i} missing field '{field}'. Keys: {list(item.keys())}"


@then('the item with "{key}" equal to "{value}" should exist')
def step_item_with_key_value_exists(context, key, value):
    items = extract_items(context.response)
    found = any(str(item.get(key)) == value for item in items)
    assert found, f"No item with {key}={value} found"


@then("the response should be a non-empty list")
def step_response_non_empty_list(context):
    items = extract_items(context.response)
    assert len(items) > 0, "Response is empty"
