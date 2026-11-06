# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps of the outbound B3/B9/B5 edge scenarios: refusals and empty results of the scoring, pilot and funnel
endpoints. Reuse the fresh-company and authentication steps of `outbound_steps.py`; nothing here consumes the seed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from behave import given, then, when

LEADS = "api/leads/v2/admin/{channel}/"


def _url(context, path: str) -> str:
    return context.api.url(LEADS.format(channel=context.channel) + path)


def _ok(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


@given("the channel has no scoring profile")
def step_no_scoring_profile(context):
    base = _url(context, "scoring-profiles/")
    for row in _ok(context.api.get(base))["results"]:
        _ok(context.api.delete(f"{base}{row['id']}/"), 204)


@given('an active scoring profile with a disqualifier on the domain text "{text}"')
def step_profile_with_disqualifier(context, text):
    step_no_scoring_profile(context)
    base = _url(context, "scoring-profiles/")
    body = {
        "key": "bdd.scoring.edge",
        "thresholds": {"S": 10, "M": 20, "L": 30},
        "rules": [{"field": "lead_type", "op": "in", "value": ["RETAILER"], "points": 30, "label": "retailer"}],
        "disqualifiers": [{"field": "domain", "op": "contains", "value": text, "label": f"domain has {text}"}],
    }
    created = _ok(context.api.post(base, json=body), 201)
    context.add_cleanup(lambda: context.api.delete(f"{base}{created['id']}/"))


@when('the company "{alias}" is scored expecting status {status:d}')
def step_score_expecting(context, alias, status):
    context.response = context.api.post(_url(context, f"companies/{context.saved[alias]}/score/"), json={})
    assert context.response.status_code == status, f"score -> {context.response.status_code}: {context.response.text}"
    context.response_data = context.response.json()


@then('the score is disqualified and segment "{segment}"')
def step_score_disqualified(context, segment):
    data = context.response_data
    assert data["disqualified"] and data["segment"] == segment, f"score: {data}"
    assert any(reason.startswith("disqualified:") for reason in data["reasons"]), f"reasons: {data['reasons']}"


@then('the error code is "{code}"')
def step_error_code(context, code):
    assert context.response_data.get("error") == code, f"body: {context.response_data}"


@when('a pilot for the company "{alias}" ends before it starts')
def step_pilot_backwards(context, alias):
    today = datetime.now(UTC).date()
    body = {
        "company_id": context.saved[alias],
        "start_date": today.isoformat(),
        "end_date": (today - timedelta(days=1)).isoformat(),
    }
    context.response = context.api.post(_url(context, "pilots/"), json=body)


@when("a pilot is started for the company id 999999999")
def step_pilot_unknown_company(context):
    body = {"company_id": 999999999, "start_date": datetime.now(UTC).date().isoformat()}
    context.response = context.api.post(_url(context, "pilots/"), json=body)


@when("the pilot report is read")
def step_pilot_report_read(context):
    context.response_data = _ok(context.api.get(_url(context, "pilots/report/")))


@then("the pilot report has every result key and a numeric total")
def step_pilot_report_shape(context):
    data = context.response_data
    assert set(data["by_result"]) >= {"pending", "success", "failure", "cancelled"}, f"report: {data}"
    assert isinstance(data["total"], int) and data["total"] >= 0
    assert {"running", "overdue", "avg_length_days", "license_switch_due"} <= set(data)


@when("the funnel report is read with a window that ends before it starts")
def step_funnel_reversed(context):
    now = datetime.now(UTC)
    params = {"date_from": (now).isoformat(), "date_to": (now - timedelta(days=1)).isoformat()}
    context.response = context.api.get(_url(context, "reports/funnel/"), params=params)


@when('the funnel report is read for the origin "{origin}"')
def step_funnel_origin(context, origin):
    context.response_data = _ok(context.api.get(_url(context, "reports/funnel/"), params={"origin": origin}))


@then("the funnel report has no companies and no transitions")
def step_funnel_empty(context):
    data = context.response_data
    assert data["companies"] == 0 and data["transitions"] == [] and data["stages"] == [], f"report: {data}"


@when('the company "{alias}" is moved to the unknown stage "{key}"')
def step_move_unknown(context, alias, key):
    url = _url(context, f"companies/{context.saved[alias]}/transition/")
    context.response = context.api.post(url, json={"stage_key": key})


@then('the companies list filtered by the origin of "{alias}" returns exactly "{alias}"')
def step_list_by_origin(context, alias):
    origin = context.saved[f"{alias}.origin"]
    rows = _ok(context.api.get(_url(context, "companies/"), params={"origin": origin}))["results"]
    assert [row["id"] for row in rows] == [context.saved[alias]], f"rows: {rows}"
    assert rows[0]["origin"] == origin
