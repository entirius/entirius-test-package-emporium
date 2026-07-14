# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for PriceManager admin API v2 testing."""

from __future__ import annotations

from behave import then, when

# --- Price edit shorthand ---


@when('I edit "{sku}" price to "{value}" in channel "{channel_idx}"')
def step_edit_price(context, sku, value, channel_idx):
    """PATCH price for a SKU in the given channel."""
    url = context.api.url(f"api/pricemanager/v2/admin/{channel_idx}/prices/{sku}/")
    context.response = context.api.patch(url, json={"value": float(value)})
    context.response_data = context.response.json()


# --- Price history assertions ---


@then("the response should contain at least {count:d} history entries")
def step_history_at_least_n(context, count):
    results = context.response_data.get("results", [])
    assert len(results) >= count, f"Expected at least {count} history entries, got {len(results)}"


@then('the response should contain at least 1 history entry with field "{field}"')
def step_history_entry_has_field(context, field):
    results = context.response_data.get("results", [])
    assert results, "No history entries in response"
    missing = [i for i, entry in enumerate(results) if field not in entry]
    assert not missing, (
        f"History entries at indices {missing} are missing field '{field}'. Entry keys: {list(results[0].keys())}"
    )


@then("the price history results should be ordered newest first")
def step_history_ordered_newest_first(context):
    results = context.response_data.get("results", [])
    if len(results) < 2:
        return
    timestamps = [entry.get("created_at", "") for entry in results]
    for i in range(len(timestamps) - 1):
        assert timestamps[i] >= timestamps[i + 1], (
            f"History not ordered newest first: entry {i} ({timestamps[i]}) "
            f"is older than entry {i + 1} ({timestamps[i + 1]})"
        )
