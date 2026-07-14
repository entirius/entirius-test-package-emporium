# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for ContentDB author BDD tests."""

from __future__ import annotations

from behave import given, then, when

from entirius_tests.assertions import extract_items

# --- Author Creation / Cleanup Helpers ---


def _find_author_by_slug(context, slug: str) -> dict | None:
    """Return author dict from list endpoint if found by slug, else None."""
    url = context.api.url("api/contentdb/v2/admin/authors/")
    resp = context.api.get(url, params={"search": slug, "page_size": 100})
    if resp.status_code != 200:
        return None
    for item in resp.json().get("results", []):
        if item.get("slug") == slug:
            return item
    return None


@given('I ensure contentdb author with slug "{slug}" is cleaned up')
def step_ensure_author_cleaned(context, slug):
    """Idempotently delete author by slug. Ignores missing author."""
    author = _find_author_by_slug(context, slug)
    if author is None:
        return
    uid = author["uid"]
    url = context.api.url(f"api/contentdb/v2/admin/authors/{uid}/")
    context.api.delete(url, json={"reassign_to": None})


@given('I create a test contentdb author "{name}" with slug "{slug}"')
def step_create_test_author(context, name, slug):
    """Create an author and save its uid to context.saved.

    Saves as 'author_uid' on first call. Subsequent calls save as
    'author_uid_1', 'author_uid_2', etc. to support multi-author scenarios.
    """
    # Clean up any leftover from a previous run
    existing = _find_author_by_slug(context, slug)
    if existing:
        uid = existing["uid"]
        url = context.api.url(f"api/contentdb/v2/admin/authors/{uid}/")
        context.api.delete(url, json={"reassign_to": None})

    url = context.api.url("api/contentdb/v2/admin/authors/")
    body = {"name": name, "slug": slug, "is_active": True}
    resp = context.api.post(url, json=body)
    assert resp.status_code == 201, f"Failed to create test author '{slug}': {resp.status_code} {resp.text[:300]}"
    uid = resp.json()["uid"]

    # Keys use the "saved." prefix so {saved.author_uid} placeholder resolution works.
    # First call: save as "saved.author_uid".
    # Second call: promote unnumbered key to "saved.author_uid_1", save as "saved.author_uid_2".
    base_key = "saved.author_uid"
    if base_key not in context.saved:
        context.saved[base_key] = uid
        return

    # Promote unnumbered key to _1 before assigning next numbered slot
    if "saved.author_uid_1" not in context.saved:
        context.saved["saved.author_uid_1"] = context.saved[base_key]

    # Find next available numbered slot starting from 2
    index = 2
    while f"saved.author_uid_{index}" in context.saved:
        index += 1
    context.saved[f"saved.author_uid_{index}"] = uid


# --- Public Endpoint Steps ---


@when('I GET the ContentDB published endpoint "{path}" with author "{author_slug}"')
def step_get_contentdb_published_with_author(context, path, author_slug):
    url = context.api.contentdb_url(f"published/{path}")
    context.response = context.api.get(url, params={"language": "EN", "access_rights": 1, "author": author_slug})
    context.response_data = context.response.json()


# --- Array Assertion Steps ---


@then('at least one result should have non-empty "{field}" array')
def step_at_least_one_non_empty_array(context, field):
    items = extract_items(context.response)
    assert len(items) > 0, "Response is empty — no results to check"
    found = any(isinstance(item.get(field), list) and len(item[field]) > 0 for item in items)
    assert found, f"No result has a non-empty '{field}' array. Values: {[item.get(field) for item in items]}"


@then('at least one result should have empty "{field}" array')
def step_at_least_one_empty_array(context, field):
    items = extract_items(context.response)
    assert len(items) > 0, "Response is empty — no results to check"
    found = any(isinstance(item.get(field), list) and len(item[field]) == 0 for item in items)
    assert found, f"No result has an empty '{field}' array. Values: {[item.get(field) for item in items]}"


@then("authors in results should have the fields")
def step_authors_in_results_have_fields(context):
    """Assert every author object in every result has the required fields."""
    items = extract_items(context.response)
    required_fields = [row["field"] for row in context.table]
    authors_checked = 0
    for i, item in enumerate(items):
        authors = item.get("authors", [])
        for j, author in enumerate(authors):
            for field in required_fields:
                assert field in author, (
                    f"Author {j} in result {i} missing field '{field}'. Author keys: {list(author.keys())}"
                )
            authors_checked += 1
    assert authors_checked > 0, "No authors found across all results — cannot verify author fields"


# --- Public Author Endpoint Steps ---


@then("every author in results should have published_post_count greater than 0")
def step_every_author_post_count_gt_zero(context):
    items = extract_items(context.response)
    assert len(items) > 0, "Response is empty — no authors to check"
    for i, item in enumerate(items):
        count = item.get("published_post_count", 0)
        assert count > 0, f"Author {i} ({item.get('slug')}) has published_post_count={count}, expected > 0"


@then("every author in results should have the fields")
def step_every_author_has_fields(context):
    items = extract_items(context.response)
    required_fields = [row["field"] for row in context.table]
    assert len(items) > 0, "Response is empty — no authors to check"
    for i, item in enumerate(items):
        for field in required_fields:
            assert field in item, f"Author {i} ({item.get('slug')}) missing field '{field}'. Keys: {list(item.keys())}"


@then('the response data field "{field}" should equal "{value}"')
def step_response_data_field_equals(context, field, value):
    data = context.response_data.get("data", {})
    actual = data.get(field)
    assert str(actual) == value, f"Expected data.{field}='{value}', got '{actual}'"


@then('the response data should have the field "{field}"')
def step_response_data_has_field(context, field):
    data = context.response_data.get("data", {})
    assert field in data, f"Response data missing field '{field}'. Keys: {list(data.keys())}"


@then('the response data field "{field}" should be greater than {n:d}')
def step_response_data_field_gt(context, field, n):
    data = context.response_data.get("data", {})
    actual = data.get(field, 0)
    assert actual > n, f"Expected data.{field} > {n}, got {actual}"
