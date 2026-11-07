# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps of the Q16/Q20 scenarios: the "what to do today" queue, the "not now" return and the daily digest. They build
on the T2a/T4 steps (fresh company, static mail, reply arrives, inbox polled). Settings a scenario changes are put back
by cleanups."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from behave import given, then, when

LEADS = "api/leads/v2/admin/{channel}/"
NOTIFICATIONS = "api/notifications/v2/admin/{channel}/notifications/?role=sales_admin&page_size=100"


def _url(context, path: str) -> str:
    return context.api.url(LEADS.format(channel=context.channel) + path)


def _json(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


def _contact(context, alias: str) -> dict:
    rows = _json(context.api.get(_url(context, f"contacts/?company={context.saved[alias]}")))["results"]
    assert rows, f"company {alias} has no contact"
    return rows[0]


def _queue(context) -> dict:
    return _json(context.api.get(_url(context, "queue/")))


@given('the "not now" window of the channel is {days:d} days')
def step_window(context, days):
    _json(context.api.patch(_url(context, "settings/"), json={"resume_days": {"not_now": days}}))
    context.add_cleanup(lambda: context.api.patch(_url(context, "settings/"), json={"resume_days": {}}))


@then('the first contact of the company "{alias}" has a planned return as "{intent}" in about {days:d} days')
def step_planned(context, alias, intent, days):
    contact = _contact(context, alias)
    assert contact["resume_intent"] == intent and contact["resume_at"], f"contact: {contact}"
    planned = datetime.fromisoformat(contact["resume_at"].replace("Z", "+00:00"))
    delta = planned - datetime.now(UTC)
    assert abs(delta - timedelta(days=days)) < timedelta(hours=2), f"planned in {delta}, expected about {days} days"


@then('the first contact of the company "{alias}" has no planned return')
def step_not_planned(context, alias):
    contact = _contact(context, alias)
    assert contact["resume_at"] is None, f"contact still has a planned return: {contact['resume_at']}"


@when('the "not now" resume of the company "{alias}" runs {days:d} days ahead')
def step_run_resume(context, alias, days):
    """Scoped to the company: the run is otherwise channel-wide and would pick up contacts of other scenarios."""
    as_of = (datetime.now(UTC) + timedelta(days=days)).isoformat()
    body = {"as_of": as_of, "company_id": context.saved[alias]}
    context.response_data = _json(context.api.post(_url(context, "test/resume-now/"), json=body))


@then("the resume run resumed {resumed:d} contacts and cancelled {cancelled:d}")
def step_resume_counts(context, resumed, cancelled):
    data = context.response_data
    assert (data["resumed"], data["cancelled"]) == (resumed, cancelled), f"resume run: {data}"


@when('the address of the first contact of the company "{alias}" is put on the do-not-contact list')
def step_dnc(context, alias):
    body = {"email": _contact(context, alias)["email"], "reason": "bdd q16 opt-out"}
    assert _json(context.api.post(_url(context, "do-not-contact/"), json=body), 201)["contacts"] >= 1


@then('the queue of the channel has a "{kind}" row for the company "{alias}" with reason "{reason}"')
def step_queue_row(context, kind, alias, reason):
    rows = [r for r in _queue(context)["items"] if r["kind"] == kind and r["company_id"] == context.saved[alias]]
    assert any(r["reason"] == reason for r in rows), f"no {kind}/{reason} row for the company in {rows}"


@then('the queue of the channel has a "{kind}" row linking to "{path}"')
def step_queue_link(context, kind, path):
    rows = [r for r in _queue(context)["items"] if r["kind"] == kind]
    assert rows and rows[0]["path"] == path and rows[0]["count"] >= 1, f"queue rows of kind {kind}: {rows}"


@then("the queue of the channel is sorted by value")
def step_queue_sorted(context):
    values = [row["value"] for row in _queue(context)["items"]]
    assert values == sorted(values, reverse=True) and len(values) >= 2, f"queue values: {values}"


@when("the daily digest is sent")
def step_digest(context):
    context.response_data = _json(context.api.post(_url(context, "test/digest-now/"), json={}))


@then("the digest reached notifications and counts at least {sent:d} sent mail")
def step_digest_notified(context, sent):
    assert context.response_data["sent"].get(context.channel) == 1, f"digest: {context.response_data}"
    rows = _json(context.api.get(context.api.url(NOTIFICATIONS.format(channel=context.channel))))["results"]
    digests = [r for r in rows if r["title"].startswith("Outbound digest")]
    assert digests, "no digest notification"
    match = re.search(r"(\d+) sent", digests[0]["title"])
    assert match and int(match[1]) >= sent, digests[0]["title"]
