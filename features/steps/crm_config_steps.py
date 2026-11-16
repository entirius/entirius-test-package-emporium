# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CRM steps for scoring, the funnel report, rule runs, suppressions and PUT on the v2 admin API. Every change to the
channel configuration is put back when the scenario ends."""

from __future__ import annotations

import json

from behave import given, then, when

from entirius_tests.crm import COMMUNICATOR, LEADS, ok, url


def _resolve(context, text: str) -> str:
    resolved = text.replace("{channel_idx}", context.channel or "")
    for key, value in context.saved.items():
        resolved = resolved.replace(f"{{{key}}}", str(value))
    return resolved


@when('I PUT to the v2 admin endpoint "{path}" with body')
def step_put_v2_admin(context, path):
    module, _, rest = _resolve(context, path).partition("/")
    target = context.api.url(f"api/{module}/v2/{rest}")
    context.response = context.api.put(target, json=json.loads(_resolve(context, context.text)))
    context.response_data = context.response.json() if context.response.content else {}


@then('the company "{alias}" has no rule run')
def step_no_rule_run(context, alias):
    """`test/import-now/` imports in the request: a rule run would exist when it answered."""
    runs = ok(context.api.get(url(context, LEADS, "rule-runs/"), params={"company": context.saved[alias]}))["results"]
    assert not runs, f"rule runs: {runs}"


@then('the suppression list does not contain the address of "{alias}"')
def step_not_suppressed(context, alias):
    status = ok(
        context.api.get(
            url(context, COMMUNICATOR, "addresses/status/"), params={"email": context.saved[f"{alias}.email"]}
        )
    )
    assert status["refusal"] is None, f"address status: {status}"


# --- Scoring ---


@given('the company "{alias}" industry is "{industry}"')
def step_industry(context, alias, industry):
    ok(context.api.patch(url(context, LEADS, f"companies/{context.saved[alias]}/"), json={"industry": industry}))


@when('the company "{alias}" is scored')
def step_score(context, alias):
    context.response = context.api.post(url(context, LEADS, f"companies/{context.saved[alias]}/score/"), json={})
    context.response_data = context.response.json()


@then('the score is segment "{segment}" with {points:d} points')
def step_score_is(context, segment, points):
    data = ok(context.response)
    assert (data["segment"], data["points"]) == (segment, points), f"score: {data}"


@then('the score is segment "{segment}" and disqualified')
def step_score_disqualified(context, segment):
    data = ok(context.response)
    assert data["segment"] == segment and data["disqualified"], f"score: {data}"


def _set_profiles(context, profiles: list[dict], active: bool) -> None:
    for profile in profiles:
        target = url(context, LEADS, f"scoring-profiles/{profile['id']}/")
        ok(context.api.patch(target, json={"is_active": active}))


@given("the scoring profile of the channel is switched off")
def step_scoring_off(context):
    rows = ok(context.api.get(url(context, LEADS, "scoring-profiles/")))["results"]
    active = [row for row in rows if row["is_active"]]
    context.add_cleanup(_set_profiles, context, active, True)
    _set_profiles(context, active, False)


# --- Funnel and list filters ---


@then('the funnel report of the origin of "{alias}" shows 1 company and a transition "{source}" to "{target}"')
def step_funnel(context, alias, source, target):
    origin = context.saved[f"{alias}.origin"]
    report = ok(context.api.get(url(context, LEADS, "reports/funnel/"), params={"origin": origin}))
    moves = [(row["from_stage"], row["to_stage"], row["count"]) for row in report["transitions"]]
    assert (source, target, 1) in moves, f"transitions: {moves}"
    assert {"origin": origin, "companies": 1} in report["origins"], f"origins: {report['origins']}"


@then('the companies filtered by the origin of "{alias}" are exactly "{expected}"')
def step_origin_filter(context, alias, expected):
    params = {"origin": context.saved[f"{alias}.origin"]}
    rows = ok(context.api.get(url(context, LEADS, "companies/"), params=params))["results"]
    assert [row["id"] for row in rows] == [context.saved[expected]], f"companies: {rows}"


@then('the results hold the saved id "{alias}"')
def step_results_hold(context, alias):
    ids = [row["id"] for row in context.response_data["results"]]
    assert context.saved[alias] in ids, f"{alias}={context.saved[alias]} not in {ids}"
