# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Access steps (`@access`): role-user login, gate refusal checks, `me` permissions, audit lookups, application
tokens on the contact-forms routes and cleanup that runs even when a scenario fails.

A raw token value lives only in `context.raw_tokens` — it is never printed, saved in `context.saved` or put in an
assertion message, and the create/rotate response bodies are stored without it. Shared with plan 17b.
"""

from __future__ import annotations

import itertools
import uuid
from datetime import UTC, datetime, timedelta

import requests
from behave import given, step, then, when

from entirius_tests.auth import obtain_jwt_token

GATE_ISSUES = frozenset({"ACCESS_DENIED", "STAFF_ONLY", "UNMAPPED_ROUTE"})
SEED_CHANNEL_POSITIONS = {"first": 0, "second": 1}
# ACCESS_TOKEN_LAST_USED_INTERVAL_S (300 s) plus slack: a token used "just now" carries a recent last_used_at.
LAST_USED_WINDOW = timedelta(minutes=10)
PAGE_SIZE = 100  # the access API's maximum
CLEANUP_STATUSES = frozenset({200, 204, 404, 409})  # done, or already gone / already revoked


def resolve(text: str, context) -> str:
    """Replace `{channel_idx}` and `{saved.*}` placeholders."""
    resolved = text.replace("{channel_idx}", context.channel or "")
    for key, value in (context.saved or {}).items():
        resolved = resolved.replace(f"{{{key}}}", str(value))
    return resolved


def api_path(path: str) -> str:
    """`access/admin/roles/` → `api/access/v2/admin/roles/`."""
    module, _, rest = path.partition("/")
    return f"api/{module}/v2/{rest}"


def gate_issues(body: object) -> set[str]:
    """Gate refusal issues in a v2 error envelope (empty for anything else)."""
    if not isinstance(body, dict) or body.get("error") != "PERMISSION_DENIED":
        return set()
    return {detail.get("issue") for detail in body.get("details") or []} & GATE_ISSUES


def without_raw(body: dict) -> dict:
    """A token create/rotate body minus its one-time `raw` value."""
    return {key: value for key, value in body.items() if key != "raw"}


def is_recent(stamp: str | None, now: datetime) -> bool:
    return stamp is not None and now - datetime.fromisoformat(stamp) <= LAST_USED_WINDOW


def _json(response: requests.Response) -> object:
    try:
        return response.json()
    except ValueError:
        return {}


def _store(context, response: requests.Response) -> None:
    context.response = response
    context.response_data = _json(response)


def _admin(context, method: str, path: str, body: dict | None = None, **kwargs) -> requests.Response:
    """A request as the superuser admin, independent of the scenario's own login."""
    if not getattr(context, "access_admin_jwt", None):
        context.access_admin_jwt = obtain_jwt_token(
            context.api.base_url, context.admin_username, context.admin_password
        )
    headers = {"Authorization": f"Bearer {context.access_admin_jwt}"}
    url = context.api.url(api_path(path))
    return requests.request(method, url, json=body, headers=headers, timeout=30, **kwargs)


def _cleanup(context, method: str, path: str, body: dict | None = None) -> None:
    """A cleanup that fails says so — a leftover grant on a seeded user would break later runs silently."""
    status = _admin(context, method, path, body).status_code
    assert status in CLEANUP_STATUSES, f"cleanup {method} {path}: HTTP {status}"


def _application_id(context, name: str) -> int:
    """Applications are never deleted, so the list grows run by run: walk every page."""
    for page in itertools.count(1):
        params = {"page": page, "page_size": PAGE_SIZE}
        body = _admin(context, "GET", "access/admin/applications/", params=params).json()
        if ids := [app["id"] for app in body["results"] if app["name"] == name]:
            return ids[0]
        assert body.get("next"), f"no application '{name}'"


def _seed_channel(context, position: str) -> str:
    return context.channels[SEED_CHANNEL_POSITIONS[position]]


# --- Setup and cleanup ---


@given("I am authenticated as the {role} staff user")
def step_auth_staff(context, role):
    assert role in context.staff_users, f"unknown role user '{role}' (known: {sorted(context.staff_users)})"
    username, password = context.staff_users[role]
    context.api.set_auth_token(obtain_jwt_token(context.api.base_url, username, password))


@given('a run-unique suffix is saved as "{alias}"')
def step_run_suffix(context, alias):
    context.saved[alias] = uuid.uuid4().hex[:10]


@given('I save the id of the {role} staff user as "{alias}"')
def step_save_staff_id(context, role, alias):
    username = context.staff_users[role][0]
    response = _admin(context, "GET", "access/admin/staff/", params={"search": username, "page_size": PAGE_SIZE})
    assert response.status_code == 200, f"staff list: HTTP {response.status_code}"
    ids = [row["id"] for row in response.json()["results"] if row["username"] == username]
    assert ids, f"staff user '{username}' not found — run the seed (scripts/seed-access.py)"
    context.saved[alias] = ids[0]


@step('the admin sends {method:w} to "{path}" when the scenario ends')
def step_cleanup(context, method, path):
    """Registered now, resolved at the end: a step that never saved its alias leaves nothing to clean."""

    def cleanup() -> None:
        resolved = resolve(path, context)
        if "{saved." not in resolved:
            _cleanup(context, method, resolved)

    context.add_cleanup(cleanup)


# --- Requests ---


@when('I GET the unknown v2 admin path "{path}"')
def step_get_any_body(context, path):
    """A 404 may answer with an HTML page — the body is not required to be JSON."""
    _store(context, context.api.get(context.api.url(api_path(resolve(path, context)))))


@then('I save the id of the result with "{key}" equal to "{value}" as "{alias}"')
def step_save_result_id(context, key, value, alias):
    ids = [row["id"] for row in context.response_data["results"] if str(row.get(key)) == value]
    assert ids, f"no result with {key} = {value}"
    context.saved[alias] = ids[0]


# --- Gate refusals ---


@then('the gate refuses with issue "{issue}"')
def step_gate_refuses(context, issue):
    body = context.response_data
    assert context.response.status_code == 403, f"expected 403, got {context.response.status_code}: {body}"
    assert body.get("error") == "PERMISSION_DENIED", f"error: {body.get('error')}"
    assert issue in gate_issues(body), f"issue {issue} not in {body.get('details')}"


@then('the refusal names "{needed}"')
def step_refusal_names(context, needed):
    descriptions = [detail.get("description") or "" for detail in context.response_data.get("details") or []]
    assert any(needed in text for text in descriptions), f"'{needed}' not in {descriptions}"


@then("the response is not a gate refusal")
def step_not_gate_refusal(context):
    issues = gate_issues(context.response_data)
    assert not issues, f"the gate answered ({sorted(issues)}) — the view should have"


# --- me ---


@then('the permission "{area}" should be "{level}"')
def step_permission_level(context, area, level):
    permissions = context.response_data["permissions"]
    assert permissions.get(area) == level, f"permissions['{area}'] = {permissions.get(area)!r}, want {level!r}"


@then('the permission "{area}" should be absent')
def step_permission_absent(context, area):
    permissions = context.response_data["permissions"]
    assert area not in permissions, f"permissions['{area}'] = {permissions[area]!r}, want absent"


@then("the catalogue should offer {areas:d} areas and {scopes:d} token scopes")
def step_catalogue_counts(context, areas, scopes):
    data = context.response_data
    area_count = sum(len(module["areas"]) for module in data["modules"])
    assert (area_count, len(data["scopes"])) == (areas, scopes), f"areas {area_count}, scopes {len(data['scopes'])}"


# --- Audit ---


def _audit_after(context, action: str, mark_alias: str) -> list[dict]:
    response = _admin(context, "GET", f"access/admin/audit/?action={action}&page_size={PAGE_SIZE}")
    assert response.status_code == 200, f"audit list: HTTP {response.status_code}"
    return [entry for entry in response.json()["results"] if entry["id"] > context.saved[mark_alias]]


@given('I save the newest audit entry id as "{alias}"')
def step_audit_mark(context, alias):
    response = _admin(context, "GET", "access/admin/audit/?page_size=1")
    assert response.status_code == 200, f"audit list: HTTP {response.status_code}"
    results = response.json()["results"]
    context.saved[alias] = results[0]["id"] if results else 0


@then('the audit log has a "{action}" entry after "{mark}" for target "{target_id}"')
def step_audit_target(context, action, mark, target_id):
    wanted = resolve(target_id, context)
    targets = [entry["target_id"] for entry in _audit_after(context, action, mark)]
    assert wanted in targets, f"no {action} entry for target {wanted} (targets since the mark: {targets})"


@then('the audit log has a "gate.bypass" entry after "{mark}" for {method:w} "{route}"')
def step_audit_bypass(context, mark, method, route):
    seen = [
        (entry["detail"].get("method"), entry["detail"].get("route"))
        for entry in _audit_after(context, "gate.bypass", mark)
    ]
    assert (method, route) in seen, f"no gate.bypass for {method} {route} (since the mark: {seen})"


@then('the audit log has no "{action}" entry after "{mark}"')
def step_audit_none(context, action, mark):
    entries = _audit_after(context, action, mark)
    assert not entries, f"unexpected {action} entries: {[entry['detail'] for entry in entries]}"


# --- Applications and tokens ---


def _keep_token(context, alias: str, response: requests.Response) -> None:
    """Keep the raw value aside, store the body without it, revoke the token when the scenario ends."""
    body = _json(response)
    assert response.status_code == 201, f"token: HTTP {response.status_code} {without_raw(body) if body else ''}"
    context.raw_tokens[alias] = body["raw"]
    context.saved[alias] = body["id"]
    context.response, context.response_data = None, without_raw(body)
    context.add_cleanup(_cleanup, context, "POST", f"access/admin/tokens/{body['id']}/revoke/")


@given('an application "{alias}" for this run')
def step_application(context, alias):
    response = _admin(context, "POST", "access/admin/applications/", {"name": f"bdd-access-{uuid.uuid4().hex}"})
    assert response.status_code == 201, f"application: HTTP {response.status_code} {_json(response)}"
    context.saved[alias] = response.json()["id"]
    context.add_cleanup(
        _cleanup, context, "PATCH", f"access/admin/applications/{context.saved[alias]}/", {"is_active": False}
    )


def _issue(context, alias: str, application: str, body: dict) -> None:
    path = f"access/admin/applications/{context.saved[application]}/tokens/"
    _keep_token(context, alias, _admin(context, "POST", path, {"name": f"bdd {alias}", **body}))


@given('a token "{alias}" of application "{application}" with scope "{scope}"')
def step_token(context, alias, application, scope):
    _issue(context, alias, application, {"scopes": [scope]})


@given('a token "{alias}" of application "{application}" with scope "{scope}" pinned to the {position} seed channel')
def step_pinned_token(context, alias, application, scope, position):
    _issue(context, alias, application, {"scopes": [scope], "channel_idx": _seed_channel(context, position)})


@when('I rotate the token "{alias}" without overlap as "{successor}"')
def step_rotate(context, alias, successor):
    response = _admin(context, "POST", f"access/admin/tokens/{context.saved[alias]}/rotate/", {"overlap_hours": 0})
    _keep_token(context, successor, response)


@when('I revoke the token "{alias}"')
def step_revoke(context, alias):
    response = _admin(context, "POST", f"access/admin/tokens/{context.saved[alias]}/revoke/")
    assert response.status_code == 200, f"revoke: HTTP {response.status_code}"
    assert response.json()["state"] == "revoked", f"state: {response.json()['state']}"


@when('I submit a contact form with the token "{alias}" on the {position} seed channel')
def step_submit_with_token(context, alias, position):
    url = context.api.url(f"api/contact-forms/v2/{_seed_channel(context, position)}/submit/")
    body = {"email": f"bdd-access-{uuid.uuid4().hex[:12]}@example.com", "body": {"name": "BDD Access"}}
    response = requests.post(url, json=body, headers={"X-API-KEY": context.raw_tokens[alias]}, timeout=30)
    response.request.headers["X-API-KEY"] = "<redacted>"  # the stored response must not carry the raw value
    _store(context, response)


# --- Legacy keys ---


@when("I make a storefront checkout call on the {position} seed channel")
def step_storefront_call(context, position):
    """The client adds the checkout fixture key to checkout URLs by itself."""
    response = context.api.get(context.api.checkout_v2_url(_seed_channel(context, position), "countries/"))
    assert response.status_code == 200, f"storefront call: HTTP {response.status_code}"


@then('the application "{name}" holds a legacy "{scope}" token without expiry, used just now')
def step_legacy_token(context, name, scope):
    tokens = _admin(context, "GET", f"access/admin/applications/{_application_id(context, name)}/tokens/").json()[
        "results"
    ]
    legacy = [token for token in tokens if token["legacy"] and scope in token["scopes"]]
    assert legacy, f"no legacy {scope} token in '{name}'"
    token = legacy[0]
    assert token["expires_at"] is None, f"legacy token expires at {token['expires_at']} (D28: never by itself)"
    assert is_recent(token["last_used_at"], datetime.now(UTC)), f"last_used_at {token['last_used_at']} is not recent"
