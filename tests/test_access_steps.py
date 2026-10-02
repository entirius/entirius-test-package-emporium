# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pure helpers of the access steps: gate refusal detection, raw-token stripping, recency, path building."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import access_steps

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def _refusal(issue: str) -> dict:
    return {"error": "PERMISSION_DENIED", "details": [{"location": "path", "issue": issue, "description": "x"}]}


def test_gate_issues_reads_the_refusal_envelope():
    assert access_steps.gate_issues(_refusal("ACCESS_DENIED")) == {"ACCESS_DENIED"}
    assert access_steps.gate_issues(_refusal("STAFF_ONLY")) == {"STAFF_ONLY"}


def test_gate_issues_ignores_view_errors_and_other_bodies():
    validation = {"error": "VALIDATION_ERROR", "details": [{"issue": "INVALID"}]}
    view_denial = {"error": "PERMISSION_DENIED", "details": []}
    assert access_steps.gate_issues(validation) == set()
    assert access_steps.gate_issues(view_denial) == set()
    assert access_steps.gate_issues([]) == set()


def test_without_raw_drops_only_the_token_value():
    assert access_steps.without_raw({"id": 7, "prefix": "ent_api_Ab3d", "raw": "secret"}) == {
        "id": 7,
        "prefix": "ent_api_Ab3d",
    }


def test_is_recent_inside_and_outside_the_window():
    inside = (NOW - timedelta(minutes=9)).isoformat()
    outside = (NOW - timedelta(minutes=11)).isoformat()
    assert access_steps.is_recent(inside, NOW)
    assert not access_steps.is_recent(outside, NOW)
    assert not access_steps.is_recent(None, NOW)


def test_is_recent_reads_the_api_z_suffix():
    assert access_steps.is_recent("2026-10-03T11:58:00.123456Z", NOW)


def test_paths_resolve_saved_aliases_and_the_channel():
    context = SimpleNamespace(channel="default-europe", saved={"saved.run": "ab12"})
    resolved = access_steps.resolve("faq/admin/{channel_idx}/groups/bdd-access-{saved.run}/", context)
    assert access_steps.api_path(resolved) == "api/faq/v2/admin/default-europe/groups/bdd-access-ab12/"
