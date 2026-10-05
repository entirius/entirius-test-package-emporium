# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Access steps (`@access`): role-user login, gate refusal checks, `me` permissions, audit lookups, application
tokens on the contact-forms routes and cleanup that runs even when a scenario fails.

A raw token value lives only in `context.raw_tokens` — it is never printed, saved in `context.saved` or put in an
assertion message, and the create/rotate response bodies are stored without it. Shared with plan 17b, whose
`@access-security` steps (callers, raw requests that control every header, token abuse, secret hygiene) close the file;
there a token value may also sit in the scenario's caller session headers, and a stored answer has it redacted.
"""

from __future__ import annotations

import itertools
import json
import re
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta

import requests
from behave import given, step, then, when

from entirius_tests.api_client import CONTACT_FORM_API_KEYS
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


def _find_id(context, path: str, field: str, value: str) -> int | None:
    """The id of the row with `field == value`, walking every page (applications are never deleted, so the list
    grows run by run)."""
    for page in itertools.count(1):
        body = _admin(context, "GET", path, params={"page": page, "page_size": PAGE_SIZE}).json()
        if ids := [row["id"] for row in body["results"] if row[field] == value]:
            return ids[0]
        if not body.get("next"):
            return None


def _find_application(context, name: str) -> int | None:
    return _find_id(context, "access/admin/applications/", "name", name)


def _application_id(context, name: str) -> int:
    application_id = _find_application(context, name)
    assert application_id is not None, f"no application '{name}'"
    return application_id


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


def _legacy_token(context, name: str, scope: str) -> dict:
    tokens = _admin(context, "GET", f"access/admin/applications/{_application_id(context, name)}/tokens/").json()[
        "results"
    ]
    legacy = [token for token in tokens if token["legacy"] and scope in token["scopes"]]
    assert legacy, f"no legacy {scope} token in '{name}'"
    return legacy[0]


@then('the application "{name}" holds a legacy "{scope}" token without expiry, used just now')
def step_legacy_token(context, name, scope):
    token = _legacy_token(context, name, scope)
    assert token["expires_at"] is None, f"legacy token expires at {token['expires_at']} (D28: never by itself)"
    assert is_recent(token["last_used_at"], datetime.now(UTC)), f"last_used_at {token['last_used_at']} is not recent"


# --- Security (`@access-security`): callers, raw requests, token abuse, audit counts, secret hygiene ---

SECURITY_APPLICATION = "bdd-access-security"  # shared and never deactivated: its tokens are revoked per scenario
SECURITY_TOKEN_TTL = timedelta(days=30)  # every token these steps issue expires (secret scopes must)
GATE_401_ISSUE = "NOT_AUTHENTICATED"
CREDENTIAL_HEADERS = ("Authorization", "Cookie", "X-API-KEY", "X-API-ADMIN-KEY")
SECRET_FIELDS = frozenset({"raw", "key_hash"})
DAYS_AHEAD = re.compile(r"\{days_ahead:(-?\d+)\}")
EXPIRY_SLACK = timedelta(minutes=10)
EXPIRES_SOON = timedelta(seconds=2)
NO_VALUE = "-"
STATUS_ONLY = "n/a"  # HEAD: no body to read
LOGIN_REDIRECT = "login redirect"
_security_application_ids: dict[str, int] = {}


def gate_answer_issues(body: object) -> set[str]:
    """Gate refusal issues plus the gate's own 401 (`NOT_AUTHENTICATED`) — a view's own answers carry neither."""
    issues = gate_issues(body)
    if isinstance(body, dict) and body.get("error") == "AUTHENTICATION_REQUIRED":
        issues |= {detail.get("issue") for detail in body.get("details") or []} & {GATE_401_ISSUE}
    return issues


def comparable(body: object) -> object:
    """An answer without its per-request `debug_id`."""
    if isinstance(body, dict):
        return {key: value for key, value in body.items() if key != "debug_id"}
    return body


def secret_fields(body: object) -> set[str]:
    """`raw` / `key_hash` keys anywhere in a JSON body."""
    if isinstance(body, dict):
        return (SECRET_FIELDS & body.keys()).union(*(secret_fields(value) for value in body.values()))
    if isinstance(body, list):
        return set().union(*(secret_fields(value) for value in body))
    return set()


def leaked_aliases(text: str, raw_tokens: dict[str, str]) -> list[str]:
    """Aliases — never values — of the raw tokens that occur in a text."""
    return sorted(alias for alias, raw in raw_tokens.items() if raw and raw in text)


def with_days_ahead(text: str, now: datetime) -> str:
    """`{days_ahead:30}` → the ISO instant 30 days after `now` (a negative count lies in the past)."""
    return DAYS_AHEAD.sub(lambda match: (now + timedelta(days=int(match.group(1)))).isoformat(), text)


def _security_application(context) -> int:
    """Looked up (or created) once per API: the application list grows with every plan-17 run."""
    base_url = context.api.base_url
    if base_url not in _security_application_ids:
        found = _find_application(context, SECURITY_APPLICATION)
        _security_application_ids[base_url] = found or _create_security_application(context)
    return _security_application_ids[base_url]


def _create_security_application(context) -> int:
    response = _admin(context, "POST", "access/admin/applications/", {"name": SECURITY_APPLICATION})
    assert response.status_code == 201, f"application: HTTP {response.status_code} {_json(response)}"
    return response.json()["id"]


def _issue_security_token(context, alias: str, body: dict) -> None:
    expires_at = (datetime.now(UTC) + SECURITY_TOKEN_TTL).isoformat()
    path = f"access/admin/applications/{_security_application(context)}/tokens/"
    request = {"name": f"bdd-security {alias}", "expires_at": expires_at, **body}
    _keep_token(context, alias, _admin(context, "POST", path, request))


def _credentials(context, who: str) -> tuple[str, str]:
    if who == "admin":
        return context.admin_username, context.admin_password
    if who == "customer":
        return context.test_username, context.test_password
    assert who in context.staff_users, f"unknown caller '{who}'"
    return context.staff_users[who]


def _token_only_headers(context) -> dict[str, str]:
    """A fresh publishable and a fresh secret token, no JWT — the gate never reads either (D12)."""
    _issue_security_token(context, "caller-publishable", {"scopes": ["checkout.storefront"]})
    _issue_security_token(context, "caller-secret", {"scopes": ["reviews.moderate"]})
    raw = context.raw_tokens
    return {"X-API-KEY": raw["caller-publishable"], "X-API-ADMIN-KEY": raw["caller-secret"]}


def _caller_headers(context, who: str) -> dict[str, str]:
    if who == "anonymous":
        return {}
    if who == "bad-bearer":
        return {"Authorization": "Bearer not-a-jwt"}
    if who == "token-only":
        return _token_only_headers(context)
    return {"Authorization": f"Bearer {obtain_jwt_token(context.api.base_url, *_credentials(context, who))}"}


def _new_caller(context, who: str, session: requests.Session) -> None:
    context.caller, context.caller_session, context.anonymous_twin = who, session, None


def _redact(response: requests.Response) -> None:
    """The stored request must not carry a credential."""
    for header in CREDENTIAL_HEADERS:
        if header in response.request.headers:
            response.request.headers[header] = "<redacted>"


def _store_answer(context, response: requests.Response) -> None:
    """Like `_store`; a one-time `raw` moves to `context.raw_tokens` (redacted in the stored body) and its token is
    revoked at the end."""
    _store(context, response)
    body = context.response_data
    context.answer_had_raw = isinstance(body, dict) and "raw" in body
    if context.answer_had_raw:
        context.raw_tokens[f"answer-{body['id']}"] = body["raw"]
        response._content = response.content.replace(body["raw"].encode(), b"<redacted>")
        context.response_data = without_raw(body)
        context.add_cleanup(_cleanup, context, "POST", f"access/admin/tokens/{body['id']}/revoke/")
    _undo_created(context, response)


def _undo_created(context, response: requests.Response) -> None:
    """A grant or application a request created — on purpose or wrongly admitted — never outlives the scenario."""
    if response.status_code != 201:
        return
    if response.url.endswith("/api/access/v2/admin/grants/"):
        path = f"access/admin/grants/{context.response_data['id']}/"
        context.add_cleanup(_cleanup, context, "DELETE", path)
    if response.url.endswith("/api/access/v2/admin/applications/"):
        path = f"access/admin/applications/{context.response_data['id']}/"
        context.add_cleanup(_cleanup, context, "PATCH", path, {"is_active": False})


def _request(context, method: str, path: str, body: str | None, session: requests.Session) -> requests.Response:
    """Exactly the session's headers, `{channel_idx}`/`{saved.*}`/`{days_ahead:N}` resolved, no redirect followed."""
    url = context.api.url(resolve(path, context))
    payload = json.loads(with_days_ahead(resolve(body, context), datetime.now(UTC))) if body else None
    response = session.request(method, url, json=payload, timeout=30, allow_redirects=False)
    _redact(response)
    return response


def _send(context, method: str, path: str, body: str | None = None) -> None:
    context.anonymous_twin = None
    session = getattr(context, "caller_session", None) or requests.Session()
    _store_answer(context, _request(context, method, path, body, session))


def _shown(context) -> str:
    return str(context.response_data)[:300]


def _assert_no_secret(context, response: requests.Response, where: str) -> None:
    fields = secret_fields(_json(response))
    leaked = leaked_aliases(response.text, context.raw_tokens)
    assert not fields and not leaked, f"{where}: secret fields {sorted(fields)}, values of the tokens {leaked}"


# Callers and keys


@given("the caller is {who}")
def step_caller(context, who):
    """anonymous | customer | bad-bearer | token-only | a staff user (norole, viewer, …, accessadmin) | admin."""
    session = requests.Session()
    session.headers.update(_caller_headers(context, who))
    _new_caller(context, who, session)


@given("the caller has a Django admin session as {who}")
def step_django_admin_session(context, who):
    session, login = requests.Session(), context.api.url("admin/login/")
    session.get(login, timeout=30)
    username, password = _credentials(context, who)
    form = {"username": username, "password": password, "csrfmiddlewaretoken": session.cookies.get("csrftoken")}
    response = session.post(login, data=form, headers={"Referer": login}, allow_redirects=False, timeout=30)
    assert response.status_code == 302, f"Django admin login as {who}: HTTP {response.status_code}"
    _new_caller(context, who, session)


def _key_value(context, key: str) -> str:
    if key == "checkout fixture":
        return context.api.checkout_api_key
    if key == "contact-forms fixture":
        return CONTACT_FORM_API_KEYS[context.channel]
    _issue_security_token(context, key, {"scopes": [key]})
    return context.raw_tokens[key]


@given("the caller presents the {key} key")
def step_caller_key(context, key):
    """`-` (none), `checkout fixture`, `contact-forms fixture` (the scenario's channel) or a fresh token of a scope."""
    if key != NO_VALUE:
        context.caller_session.headers["X-API-KEY"] = _key_value(context, key)


@given('I save the caller\'s own user id as "{alias}"')
def step_save_own_id(context, alias):
    response = _request(context, "GET", "api/access/v2/me/", None, context.caller_session)
    assert response.status_code == 200, f"me: HTTP {response.status_code}"
    context.saved[alias] = response.json()["user"]["id"]


# Raw requests and their answers


@when('the caller sends {method:w} to "{path}"')
def step_caller_sends(context, method, path):
    """POST carries an empty JSON object. A token-only caller's request is repeated anonymously to compare (D12)."""
    body = "{}" if method == "POST" else None
    _send(context, method, path, body)
    if context.caller == "token-only":
        twin = _request(context, method, path, body, requests.Session())
        context.anonymous_twin = (twin.status_code, comparable(_json(twin)))


@when('the caller sends {method:w} to "{path}" with JSON {body}')
def step_caller_sends_json(context, method, path, body):
    _send(context, method, path, None if body == NO_VALUE else body)


@when('the caller sends {method:w} to "{path}" with body')
def step_caller_sends_body(context, method, path):
    _send(context, method, path, context.text)


def _check_issue(context, issue: str) -> None:
    if issue == STATUS_ONLY:
        return
    if issue == LOGIN_REDIRECT:
        location = context.response.headers.get("Location", "")
        assert location.startswith("/admin/login/"), f"Location {location!r}, want the admin login"
        return
    issues = gate_answer_issues(context.response_data)
    expected = set() if issue == NO_VALUE else {issue}
    assert issues == expected, f"gate issues {sorted(issues)}, want {sorted(expected)}: {_shown(context)}"


@then('the answer is {status:d} with "{issue}"')
def step_answer(context, status, issue):
    """`issue`: a gate issue, `-` (no gate issue), `n/a` (status only) or `login redirect`."""
    got = context.response.status_code
    assert got == status, f"expected {status}, got {got}: {_shown(context)}"
    _check_issue(context, issue)
    if twin := getattr(context, "anonymous_twin", None):
        mine = (got, comparable(context.response_data))
        assert mine == twin, f"token-only answer {mine} differs from the anonymous one {twin}"


@then('the answer does not contain "{text}"')
def step_answer_lacks(context, text):
    assert text == NO_VALUE or text not in context.response.text, f"'{text}' in {_shown(context)}"


@then('the answer names the issue "{issue}"')
def step_answer_issue(context, issue):
    if issue == NO_VALUE:
        return
    issues = [detail.get("issue") for detail in context.response_data.get("details") or []]
    assert issue in issues, f"issue {issue} not in {issues}"


@then("the answer carries no token secret")
def step_answer_no_secret(context):
    _assert_no_secret(context, context.response, "answer")


@then("the answer was a one-time secret marked no-store")
def step_answer_one_time(context):
    assert context.answer_had_raw, f"no raw value in the answer: {_shown(context)}"
    cache_control = context.response.headers.get("Cache-Control", "")
    assert "no-store" in cache_control, f"Cache-Control: {cache_control!r}"


@then("the answered expiry is {days:d} days ahead")
def step_answered_expiry(context, days):
    expires_at = datetime.fromisoformat(context.response_data["expires_at"])
    offset = expires_at - datetime.now(UTC) - timedelta(days=days)
    assert abs(offset) < EXPIRY_SLACK, f"expires_at {expires_at} is not {days} days ahead"


@then('I keep the answer as "{label}"')
def step_keep_answer(context, label):
    context.answers = {**(getattr(context, "answers", None) or {}), label: context.response}


# Token abuse


@given('an unknown token value "{alias}"')
def step_unknown_token(context, alias):
    context.raw_tokens[alias] = f"ent_api_{secrets.token_urlsafe(32)}"


@given('an oversized token value "{alias}" of {size:d} characters')
def step_oversized_token(context, alias, size):
    context.raw_tokens[alias] = "x" * size


@given('the shared security application is saved as "{alias}"')
def step_security_application(context, alias):
    """One application for every run: tokens issued in it are revoked per scenario, the application stays."""
    context.saved[alias] = _security_application(context)


@given('a security token "{alias}" with scope "{scope}"')
def step_security_token(context, alias, scope):
    _issue_security_token(context, alias, {"scopes": [scope]})


@given('a security token "{alias}" with scope "{scope}" pinned to the {position} seed channel')
def step_pinned_security_token(context, alias, scope, position):
    _issue_security_token(context, alias, {"scopes": [scope], "channel_idx": _seed_channel(context, position)})


@given('a security token "{alias}" with scope "{scope}" pinned to the {position} seed channel that has expired')
def step_expired_security_token(context, alias, scope, position):
    """Issued to expire in two seconds, then waited out: the API never takes an expiry in the past."""
    expires_at = datetime.now(UTC) + EXPIRES_SOON
    channel_idx = _seed_channel(context, position)
    body = {"scopes": [scope], "channel_idx": channel_idx, "expires_at": expires_at.isoformat()}
    _issue_security_token(context, alias, body)
    time.sleep((expires_at - datetime.now(UTC)).total_seconds() + 1)


@when('the tokens "{aliases}" are sent in "{header}" with {method:w} to "{path}"')
def step_send_tokens(context, aliases, header, method, path):
    """One request per token, each alone in `header` (`Authorization` carries it as a Bearer value); body = docstring."""
    context.answers = {}
    for alias in (name.strip() for name in aliases.split(",")):
        raw = context.raw_tokens[alias]
        session = requests.Session()
        session.headers[header] = f"Bearer {raw}" if header == "Authorization" else raw
        context.answers[alias] = _request(context, method, path, context.text, session)


@then("every answer is the same {status:d}")
def step_answers_identical(context, status):
    statuses = {alias: response.status_code for alias, response in context.answers.items()}
    assert set(statuses.values()) == {status}, f"statuses {statuses}, want {status}"
    bodies = {repr(comparable(_json(response)) or response.text) for response in context.answers.values()}
    assert len(bodies) == 1, f"{len(bodies)} different bodies across {sorted(context.answers)}"


@then("every answer is a client error")
def step_answers_4xx(context):
    statuses = {alias: response.status_code for alias, response in context.answers.items()}
    assert all(400 <= status < 500 for status in statuses.values()), f"statuses {statuses}"


@then("no answer carries a token secret")
def step_answers_no_secret(context):
    for alias, response in context.answers.items():
        _assert_no_secret(context, response, f"answer to '{alias}'")


@given('I save the id of the legacy "{scope}" token of application "{name}" as "{alias}"')
def step_save_legacy_id(context, scope, name, alias):
    context.saved[alias] = _legacy_token(context, name, scope)["id"]


@given('the expiry of token "{alias}" is cleared when the scenario ends')
def step_expiry_cleanup(context, alias):
    path = f"access/admin/tokens/{context.saved[alias]}/expiry/"
    context.add_cleanup(_cleanup, context, "POST", path, {"expires_at": None})


# Roles and the catalogue


def _role_id(context, key: str) -> int | None:
    return _find_id(context, "access/admin/roles/", "key", key)


def _delete_role(context, key: str) -> None:
    if (role_id := _role_id(context, resolve(key, context))) is not None:
        _cleanup(context, "DELETE", f"access/admin/roles/{role_id}/")


@given('the role "{key}" is deleted when the scenario ends')
def step_role_cleanup(context, key):
    """Resolved at the end and looked up by key: also removes a role a wrongly accepted request created."""
    context.add_cleanup(_delete_role, context, key)


@then('the role "{key}" does not exist')
def step_role_absent(context, key):
    assert _role_id(context, resolve(key, context)) is None, f"role {resolve(key, context)} exists"


@then('the role "{alias}" holds exactly the permissions {permissions}')
def step_role_permissions(context, alias, permissions):
    held = _admin(context, "GET", f"access/admin/roles/{context.saved[alias]}/").json()["permissions"]
    assert held == json.loads(permissions), f"permissions {held}"


@then('the catalogue area "{key}" is not assignable')
def step_area_not_assignable(context, key):
    areas = {area["key"]: area for module in context.response_data["modules"] for area in module["areas"]}
    assert areas[key]["assignable"] is False, f"{key}: {areas[key]}"


# Audit counts


def _bypasses(context, mark: str, method: str, route: str) -> list[dict]:
    entries = _audit_after(context, "gate.bypass", mark)
    return [
        entry["detail"] for entry in entries if (entry["detail"]["method"], entry["detail"]["route"]) == (method, route)
    ]


@then('the audit log counts {count:d} "gate.bypass" after "{mark}" for {method:w} "{route}"')
def step_bypass_count(context, count, mark, method, route):
    found = _bypasses(context, mark, method, route)
    assert len(found) == count, f"{len(found)} gate.bypass for {method} {route}, want {count}: {found}"


@then('the audit log counts {count:d} "gate.bypass" after "{mark}" for {method:w} "{route}" with status {status:d}')
def step_bypass_count_status(context, count, mark, method, route, status):
    found = _bypasses(context, mark, method, route)
    assert [entry.get("status") for entry in found] == [status] * count, f"gate.bypass for {method} {route}: {found}"


@then('the audit log counts {count:d} "{action}" after "{mark}" for target "{target_id}"')
def step_action_count(context, count, action, mark, target_id):
    wanted = resolve(target_id, context)
    found = [entry for entry in _audit_after(context, action, mark) if entry["target_id"] == wanted]
    assert len(found) == count, f"{len(found)} {action} entries for target {wanted}, want {count}"
