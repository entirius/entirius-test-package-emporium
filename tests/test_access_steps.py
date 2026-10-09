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


def test_gate_answer_issues_adds_only_the_gates_own_401():
    gate_401 = {"error": "AUTHENTICATION_REQUIRED", "details": [{"location": "header", "issue": "NOT_AUTHENTICATED"}]}
    view_401 = {"error": "AUTHENTICATION_REQUIRED", "details": []}
    assert access_steps.gate_answer_issues(gate_401) == {"NOT_AUTHENTICATED"}
    assert access_steps.gate_answer_issues(view_401) == set()
    assert access_steps.gate_answer_issues(_refusal("STAFF_ONLY")) == {"STAFF_ONLY"}


def test_comparable_drops_only_the_debug_id():
    assert access_steps.comparable({"error": "X", "debug_id": "ab12cd34", "details": []}) == {
        "error": "X",
        "details": [],
    }
    assert access_steps.comparable("text") == "text"


def test_secret_fields_finds_nested_keys():
    body = {"results": [{"id": 1, "detail": {"key_hash": "x"}}, {"raw": "y"}], "count": 2}
    assert access_steps.secret_fields(body) == {"key_hash", "raw"}
    assert access_steps.secret_fields({"prefix": "ent_api_Ab3d", "last_four": "wxyz"}) == set()


def test_leaked_aliases_names_aliases_never_values():
    raw_tokens = {"kept": "ent_api_secretvalue", "other": "ent_api_unseen", "empty": ""}
    assert access_steps.leaked_aliases('{"echo": "ent_api_secretvalue"}', raw_tokens) == ["kept"]


def test_with_days_ahead_fills_future_and_past_instants():
    text = '{"a": "{days_ahead:30}", "b": "{days_ahead:-1}"}'
    filled = access_steps.with_days_ahead(text, NOW)
    assert (
        filled == f'{{"a": "{(NOW + timedelta(days=30)).isoformat()}", "b": "{(NOW - timedelta(days=1)).isoformat()}"}}'
    )


def test_pinned_legacy_picks_the_token_of_one_channel():
    tokens = [
        {"id": 1, "legacy": True, "scopes": ["checkout.storefront"], "channel_idx": "default-europe"},
        {"id": 2, "legacy": True, "scopes": ["checkout.storefront"], "channel_idx": "default-local"},
        {"id": 3, "legacy": False, "scopes": ["checkout.storefront"], "channel_idx": "default-local"},
        {"id": 4, "legacy": True, "scopes": ["agreements.public"], "channel_idx": "default-local"},
    ]
    picked = access_steps.pinned_legacy(tokens, "checkout.storefront", "default-local")
    assert [token["id"] for token in picked] == [2]


def test_one_time_field_names_a_token_raw_or_a_generated_password():
    assert access_steps.one_time_field({"id": 1, "raw": "x"}) == "raw"
    assert access_steps.one_time_field({"id": 1, "password": "x"}) == "password"
    assert access_steps.one_time_field({"id": 1, "password": None}) is None
    assert access_steps.one_time_field({"password": "x"}) is None
    assert access_steps.one_time_field([]) is None


def test_answer_field_walks_keys_and_list_indexes():
    body = {"grants": [{"id": 31}], "data": {"deleted": True}}
    assert access_steps.answer_field(body, "grants.0.id") == 31
    assert access_steps.answer_field(body, "data.deleted") is True
