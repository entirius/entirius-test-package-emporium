# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps of the Q15 scenarios: sending health, the health policy, manual pause and resume of a sender route.
Each scenario removes the routes it made and puts the health policy back to its defaults."""

from __future__ import annotations

import time

from behave import given, then, when

ADMIN = "api/communicator/v2/admin/{channel}/"
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."
DEFAULT_POLICY = {
    "enabled": False,
    "window_hours": 168,
    "min_sample": 50,
    "max_bounce_pct": 2,
    "max_optout_pct": 3,
    "max_complaint_pct": 0.1,
}


def _url(context, path: str = "") -> str:
    return context.api.url(ADMIN.format(channel=context.channel) + path)


def _ok(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


def _remove_route(context, key: str) -> None:
    context.api.delete(_url(context, f"routes/{key}/"))


def _reset_policy(context) -> None:
    context.api.put(_url(context, "health/policy/"), json=DEFAULT_POLICY)


def _route_health(context, key: str) -> dict:
    rows = {row["route_key"]: row for row in _ok(context.api.get(_url(context, "health/")))["routes"]}
    assert key in rows, f"routes in health: {sorted(rows)}"
    return rows[key]


@given('the q15 route "{key}" exists')
def step_route(context, key):
    """A fresh mailbox per run; a route left by an earlier failed run is replaced."""
    _remove_route(context, key)
    body = {"key": key, "name": "BDD", "from_email": f"bdd-{time.time_ns()}@ecom.example.test"}
    _ok(context.api.post(_url(context, "routes/"), json=body), 201)
    context.add_cleanup(_remove_route, context, key)


@then("the health policy is off with the safe thresholds")
def step_policy_default(context):
    context.add_cleanup(_reset_policy, context)
    assert _ok(context.api.get(_url(context, "health/policy/"))) == {
        **DEFAULT_POLICY,
        "max_bounce_pct": 2.0,
        "max_optout_pct": 3.0,
    }


@then("saving the health policy with a minimum sample of {sample:d} is refused with status {status:d}")
def step_policy_refused(context, sample, status):
    response = context.api.put(_url(context, "health/policy/"), json={"min_sample": sample})
    assert response.status_code == status, f"{response.status_code} {response.text[:200]}"


@when("I switch the health policy on with a minimum sample of {sample:d} and a bounce limit of {pct:d} percent")
def step_policy_on(context, sample, pct):
    context.add_cleanup(_reset_policy, context)
    body = {**DEFAULT_POLICY, "enabled": True, "min_sample": sample, "max_bounce_pct": pct}
    _ok(context.api.put(_url(context, "health/policy/"), json=body))


@then("the health policy is on with a minimum sample of {sample:d} and a bounce limit of {pct:d} percent")
def step_policy_is_on(context, sample, pct):
    policy = _ok(context.api.get(_url(context, "health/policy/")))
    assert (policy["enabled"], policy["min_sample"], policy["max_bounce_pct"]) == (True, sample, pct), policy


@given('the health of the route "{key}" is read as "{alias}"')
def step_read_health(context, key, alias):
    context.saved[alias] = _route_health(context, key)


@when('I queue an approved "{template_key}" message to "{address}" on the q15 route "{route}" as "{alias}"')
def step_queue(context, template_key, address, route, alias):
    body = {
        "template_key": template_key,
        "recipient": {"email": address, "first_name": "Jan", "language": "pl", "legal_footer": LEGAL_FOOTER},
        "context": {"company_name": "Example Shop 1", "body": "BDD wiadomość testowa."},
        "subject_ref": f"bdd:q15:{time.time_ns()}",
        "requires_review": False,
        "sender_route": route,
    }
    data = _ok(context.api.post(_url(context, "test/communicate/"), json=body), 201)
    assert data["status"] == "approved", data
    context.saved[alias] = data["id"]


@then('the route "{key}" has sent {n:d} more in the 24h and 7d windows than "{alias}"')
def step_sent_more(context, key, n, alias):
    before, now = context.saved[alias]["windows"], _route_health(context, key)["windows"]
    for window in ("24h", "7d"):
        assert now[window]["sent"] - before[window]["sent"] == n, (window, before[window], now[window])
        assert now[window]["hard_bounce_rate_pct"] == 0.0, now[window]


@then('the channel health covers at least the sent count of "{key}"')
def step_channel_covers(context, key):
    body = _ok(context.api.get(_url(context, "health/")))
    route = _route_health(context, key)
    for window in ("24h", "7d"):
        assert body["channel"]["windows"][window]["sent"] >= route["windows"][window]["sent"] >= 1


@when('I pause the route "{key}" with the reason "{reason}"')
def step_pause(context, key, reason):
    data = _ok(context.api.post(_url(context, f"routes/{key}/pause/"), json={"reason": reason}))
    assert data["paused"] is True and data["paused_at"], data


@then('pausing the route "{key}" again is refused with status {status:d}')
def step_pause_refused(context, key, status):
    response = context.api.post(_url(context, f"routes/{key}/pause/"), json={"reason": "bdd second pause"})
    assert response.status_code == status, f"{response.status_code} {response.text[:200]}"


@then('resuming the route "{key}" without a reason is refused with status {status:d}')
def step_resume_refused(context, key, status):
    response = context.api.post(_url(context, f"routes/{key}/resume/"), json={})
    assert response.status_code == status, f"{response.status_code} {response.text[:200]}"


@when('I resume the route "{key}" with the reason "{reason}"')
def step_resume(context, key, reason):
    data = _ok(context.api.post(_url(context, f"routes/{key}/resume/"), json={"reason": reason}))
    assert data["paused"] is False, data


@then('the route "{key}" is paused')
def step_is_paused(context, key):
    assert _route_health(context, key)["paused"] is True


@then('the route "{key}" is not paused')
def step_is_not_paused(context, key):
    assert _route_health(context, key)["paused"] is False


@then('the pause log lists "pause" then "resume" for "{key}" with the reasons')
def step_log(context, key):
    rows = [r for r in _ok(context.api.get(_url(context, "health/log/")))["results"] if r["route_key"] == key]
    pair = [(r["action"], r["trigger"], r["reason"], bool(r["user"])) for r in reversed(rows)]
    assert pair[-2:] == [  # the log keeps the rows of earlier runs of the same route key
        ("pause", "manual", "bdd check of the brake", True),
        ("resume", "manual", "bdd brake released", True),
    ], pair
