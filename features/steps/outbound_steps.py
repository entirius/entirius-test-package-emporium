# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps of the outbound roadmap scenarios (T2a): a fresh imported company per scenario, a static mail sent through
the review queue and the sandbox, and the autostart sequence of the channel. Need `the channel is the primary
channel`, an authenticated admin and the sandbox mode; nothing here consumes the seed."""

from __future__ import annotations

import io
import time
from datetime import UTC, datetime, timedelta

from behave import given, then, when

from entirius_tests import clock

HEADER = (
    "company_name,domain,website,lead_type,industry,first_name,last_name,email,job_title,language,legal_basis,phone"
)
LEADS = "api/leads/v2/admin/{channel}/"
COMMUNICATOR = "api/communicator/v2/admin/{channel}/"
IMPORT_TIMEOUT_S = 60
POLL_TIMEOUT_S = 60


def _url(context, base: str, path: str = "") -> str:
    return context.api.url(base.format(channel=context.channel) + path)


def _json(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


def _poll(check, timeout: float = POLL_TIMEOUT_S):
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value or time.monotonic() > deadline:
            return value
        time.sleep(1)


@given('a fresh company is imported as "{alias}"')
@when('a fresh company is imported as "{alias}"')
def step_fresh_company(context, alias):
    """One CSV row with a unique domain and address through `test/import-now/`; saves the company id as `alias`."""
    _import_fresh(context, alias, "")


@given('a fresh company with origin "{origin}" is imported as "{alias}"')
def step_fresh_company_with_origin(context, origin, alias):
    """Same, with the `origin` column (roadmap B5); the origin is made unique per run and saved as `{alias}.origin`."""
    _import_fresh(context, alias, f"{origin}-{time.time_ns()}")


def _import_fresh(context, alias: str, origin: str) -> None:
    token = time.time_ns()
    domain, address = f"bdd-{token}.test", f"owner@bdd-{token}.test"
    header, row = HEADER, f"BDD {token},{domain},,RETAILER,garden,Ewa,Nowak,{address},Owner,pl,legitimate_interest,"
    if origin:
        header, row = f"{HEADER},origin", f"{row},{origin}"
    content = io.BytesIO(f"{header}\n{row}\n".encode())
    response = context.api.post(
        _url(context, LEADS, "test/import-now/"), files={"file": ("bdd-outbound.csv", content, "text/csv")}
    )
    batch = _json(response)
    done = _poll(
        lambda: _json(context.api.get(_url(context, LEADS, f"imports/{batch['id']}/"))).get("status") == "done"
    )
    assert done, f"import batch {batch['id']} did not finish"
    found = _json(context.api.get(_url(context, LEADS, f"companies/?search={domain}")))["results"]
    assert len(found) == 1, f"expected one company {domain}, found {len(found)}"
    context.saved[alias] = found[0]["id"]
    context.saved[f"{alias}.email"] = address
    if origin:
        context.saved[f"{alias}.origin"] = origin


@when('the company "{alias}" is contacted with the static mail "{template_key}"')
def step_contact_company(context, alias, template_key):
    """Draft through the company's communicate endpoint, accept it in the review queue, run the send beat."""
    company_id = context.saved[alias]
    detail = _json(context.api.get(_url(context, LEADS, f"companies/{company_id}/")))
    contact = next(c for c in detail["contacts"] if c["email"] == context.saved[f"{alias}.email"])
    drafted = _json(
        context.api.post(
            _url(context, LEADS, f"companies/{company_id}/communicate/"),
            json={"template_key": template_key, "contact_id": contact["id"]},
        ),
        201,
    )
    message_id = drafted["message_id"]
    _json(context.api.post(_url(context, COMMUNICATOR, f"review/{message_id}/accept/"), json={}))
    _json(clock.run_beat_send(context.api, context.channel))
    sent = _json(context.api.get(_url(context, COMMUNICATOR, "messages/?status=sent&page_size=100")))["results"]
    assert any(m["id"] == message_id for m in sent), f"message {message_id} was not sent"
    context.saved[f"{alias}.message"] = message_id


def _set_autostart(context, sequence_id: int, value: bool) -> None:
    _json(context.api.patch(_url(context, COMMUNICATOR, f"sequences/{sequence_id}/"), json={"autostart": value}))


@given('the sequence "{key}" is the autostart sequence of the channel')
def step_autostart_sequence(context, key):
    """Switched off again when the scenario ends, so later features send without follow-ups."""
    rows = _json(context.api.get(_url(context, COMMUNICATOR, "sequences/")))["results"]
    sequence = next((row for row in rows if row["key"] == key), None)
    assert sequence, f"sequence {key} is not seeded"
    for row in rows:
        if row["autostart"] and row["id"] != sequence["id"]:
            _set_autostart(context, row["id"], False)
    _set_autostart(context, sequence["id"], True)
    context.add_cleanup(_set_autostart, context, sequence["id"], False)
    context.saved["autostart_sequence"] = sequence["id"]


@then('the first thread about the company "{alias}" runs the sequence "{key}" with a follow-up due')
def step_thread_runs_sequence(context, alias, key):
    ref = f"leads.Company:{context.saved[alias]}"
    threads = _json(context.api.get(_url(context, COMMUNICATOR, f"threads/?subject_ref={ref}")))["results"]
    assert threads, f"no thread about {ref}"
    detail = _json(context.api.get(_url(context, COMMUNICATOR, f"threads/{threads[0]['id']}/")))
    state = detail.get("sequence")
    assert state, f"thread {threads[0]['id']} has no sequence state"
    assert state["sequence_id"] == context.saved["autostart_sequence"], f"state: {state}"
    assert not state["stopped_at"] and state["next_due_at"], f"sequence is not running with a due date: {state}"


# --- Roadmap B (T3): scoring, pilots, funnel report ---


@given("an active scoring profile that gives retailers 30 points")
def step_scoring_profile(context):
    """Thresholds S10, M20, L30; removed again when the scenario ends. The channel keeps one profile per key."""
    base = _url(context, LEADS, "scoring-profiles/")
    for row in _json(context.api.get(base))["results"]:
        _json(context.api.delete(f"{base}{row['id']}/"), 204)
    body = {
        "key": "bdd.scoring",
        "thresholds": {"S": 10, "M": 20, "L": 30},
        "rules": [{"field": "lead_type", "op": "in", "value": ["RETAILER"], "points": 30, "label": "retailer"}],
        "disqualifiers": [],
    }
    created = _json(context.api.post(base, json=body), 201)
    context.add_cleanup(lambda: context.api.delete(f"{base}{created['id']}/"))


@when('the company "{alias}" is scored')
def step_score_company(context, alias):
    context.response = context.api.post(_url(context, LEADS, f"companies/{context.saved[alias]}/score/"), json={})
    context.response_data = _json(context.response)


@then('the score is segment "{segment}" with {points:d} points')
def step_score_is(context, segment, points):
    data = context.response_data
    assert (data["segment"], data["points"]) == (segment, points), f"score: {data}"


@when('a pilot of 30 days is started for the company "{alias}"')
def step_start_pilot(context, alias):
    start = datetime.now(UTC).date()
    body = {
        "company_id": context.saved[alias],
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=30)).isoformat(),
        "success_criterion": "10 orders in 30 days",
    }
    pilot = _json(context.api.post(_url(context, LEADS, "pilots/"), json=body), 201)
    context.saved[f"{alias}.pilot"] = pilot["id"]


@when('the pilot of the company "{alias}" is marked "{result}"')
def step_pilot_result(context, alias, result):
    url = _url(context, LEADS, f"pilots/{context.saved[f'{alias}.pilot']}/")
    assert _json(context.api.patch(url, json={"result": result}))["result"] == result


@then("the pilot report counts at least {count:d} successful pilot")
def step_pilot_report(context, count):
    report = _json(context.api.get(_url(context, LEADS, "pilots/report/")))
    assert report["by_result"].get("success", 0) >= count, f"report: {report}"


@when('the company "{alias}" moves to the stage "{key}"')
def step_move_company(context, alias, key):
    _json(
        context.api.post(_url(context, LEADS, f"companies/{context.saved[alias]}/transition/"), json={"stage_key": key})
    )


@then('the funnel report of the origin of "{alias}" shows 1 company and a transition "{source}" to "{target}"')
def step_funnel_report(context, alias, source, target):
    origin = context.saved[f"{alias}.origin"]
    report = _json(context.api.get(_url(context, LEADS, f"reports/funnel/?origin={origin}")))
    assert report["companies"] == 1, f"report: {report}"
    moves = [(t["from_stage"], t["to_stage"], t["count"]) for t in report["transitions"]]
    assert (source, target, 1) in moves, f"transitions: {moves}"
    assert {"origin": origin, "companies": 1} in report["origins"], f"origins: {report['origins']}"
