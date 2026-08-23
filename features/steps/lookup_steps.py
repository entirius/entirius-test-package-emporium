# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for the `@lookup` suite — everything the shared admin-v2 steps don't cover:
multipart image upload and "is this ref present in that response list" assertions (the lookup API's
lists are keyed `hits` / `candidates` / `possible_duplicates`, never the generic `results`)."""

from __future__ import annotations

from pathlib import Path

from behave import given, then, when


def _fixture_image_path(context, filename: str) -> Path:
    """`fixtures/lookup/img/` sits next to `package/` (`context.test_package_path`'s parent)."""
    return Path(context.test_package_path).parent / "fixtures" / "lookup" / "img" / filename


@given('I use the lookup fixture image "{filename}"')
def step_use_lookup_image(context, filename):
    path = _fixture_image_path(context, filename)
    assert path.is_file(), f"lookup fixture image not found: {path}"
    context.lookup_image_path = path


@when('I POST an image to the lookup admin endpoint "{path}"')
def step_post_lookup_image(context, path):
    url = context.api.url(f"api/lookup/v2/admin/{path}")
    with context.lookup_image_path.open("rb") as handle:
        context.response = context.api.post(url, files={"image": (context.lookup_image_path.name, handle, "image/png")})
    context.response_data = context.response.json()


@then('the response field "{field}" should contain a candidate for "{ref}"')
def step_field_contains_candidate(context, field, ref):
    items = context.response_data.get(field) or []
    match = next((item for item in items if item.get("ref") == ref), None)
    refs = [item.get("ref") for item in items]
    assert match is not None, f"No candidate ref={ref!r} in '{field}'. Refs seen: {refs}"
    context.saved["lookup_candidate"] = match


@then('the response field "{field}" should not equal "{value}"')
def step_field_not_equal(context, field, value):
    actual = context.response_data.get(field)
    assert str(actual) != value, f"Expected '{field}' != '{value}', got '{actual}'"
