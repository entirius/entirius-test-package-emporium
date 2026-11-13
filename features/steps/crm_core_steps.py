# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CRM steps for owners, custom fields, rule conditions, tasks, the due reminder, the bell and mail written by hand.
A scenario that logs in as a staff user keeps that login: later steps run as that user."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime

from behave import given, then, when

from entirius_tests.auth import obtain_jwt_token
from entirius_tests.crm import LEADS, TODO, ok, poll, staff_id, url
from entirius_tests.stock_alerts import service_shell

NOTIFICATIONS = "api/notifications/v2/admin/{channel}/"
REMIND = "from django_todo.tasks.remind import remind_due\nprint('REMINDED', remind_due())\n"


@contextmanager
def as_role(context, role: str):
    """Requests as the staff user of `role`; the admin login comes back whatever happens."""
    username, password = context.staff_users[role]
    context.api.set_auth_token(obtain_jwt_token(context.api.base_url, username, password))
    try:
        yield
    finally:
        token = obtain_jwt_token(context.api.base_url, context.admin_username, context.admin_password)
        context.api.set_auth_token(token)


def company_ids(context, params: dict) -> list[int]:
    rows = ok(context.api.get(url(context, LEADS, "companies/"), params={**params, "page_size": 100}))["results"]
    return [row["id"] for row in rows]


@then('the company "{alias}" {verb} in the {role} staff user\'s list filtered by the owner "{owner}"')
def step_owner_filter(context, alias, verb, role, owner):
    with as_role(context, role):
        ids = company_ids(context, {"owner": owner, "search": context.saved[f"{alias}.domain"]})
    assert (context.saved[alias] in ids) == (verb == "is"), f"owner={owner}: {ids}"


@then('the company "{alias}" {verb} in the list filtered by the field "{key}" equal to "{value}"')
def step_field_filter(context, alias, verb, key, value):
    ids = company_ids(context, {f"attr.{key}": value, "search": context.saved[f"{alias}.domain"]})
    assert (context.saved[alias] in ids) == (verb == "is"), f"attr.{key}={value}: {ids}"


@then('the company "{alias}" has the field "{key}" equal to "{value}"')
def step_field_value(context, alias, key, value):
    company = ok(context.api.get(url(context, LEADS, f"companies/{context.saved[alias]}/")))
    assert company["attributes"].get(key) == value, f"attributes: {company['attributes']}"


# --- Rule conditions ---


@given('an active scoring rule on the stage "{stage}" for companies whose "{field}" is "{value}"')
def step_condition_rule(context, stage, field, value):
    stages = ok(context.api.get(url(context, LEADS, "stages/")))["results"]
    stage_id = next(row["id"] for row in stages if row["key"] == stage)
    body = {"trigger": "stage_entered", "stage_id": stage_id, "action": "score", "cooldown_hours": 0, "order": 999}
    body["conditions"] = [{"field": field, "op": "eq", "value": value}]
    rule = ok(context.api.post(url(context, LEADS, "rules/"), json=body), 201)
    context.add_cleanup(context.api.delete, url(context, LEADS, f"rules/{rule['id']}/"))
    context.saved["condition_rule"] = rule["id"]


@when('the rules of the stage "{stage}" are evaluated for the companies "{first}" and "{second}"')
def step_evaluate(context, stage, first, second):
    for alias in (first, second):
        body = {"company_id": context.saved[alias], "trigger": "stage_entered", "stage_key": stage}
        runs = ok(context.api.post(url(context, LEADS, "test/evaluate/"), json=body))["runs"]
        context.saved[f"{alias}.runs"] = {run["rule_id"]: run["outcome"] for run in runs}


@then('the scoring rule fired for "{fired}" and was skipped for "{skipped}"')
def step_condition_outcome(context, fired, skipped):
    rule = context.saved["condition_rule"]
    assert context.saved[f"{fired}.runs"].get(rule) == "fired", context.saved[f"{fired}.runs"]
    assert context.saved[f"{skipped}.runs"].get(rule) == "skipped", context.saved[f"{skipped}.runs"]


# --- Tasks and the bell ---


@when('a {kind} task "{title}" due now is created about the company "{alias}" for the {role} staff user')
def step_create_task(context, kind, title, alias, role):
    owner = staff_id(context, role)
    body = {"subject_ref": f"leads.Company:{context.saved[alias]}", "subject_label": f"BDD {alias}", "title": title}
    body |= {"kind": kind, "due_at": datetime.now(UTC).isoformat(), "owner_id": owner}
    task = ok(context.api.post(url(context, TODO, "tasks/"), json=body), 201)
    context.saved[f"{alias}.task"] = task["id"]


@then('the task of the company "{alias}" is on the today list of the {role} staff user')
def step_today_of(context, alias, role):
    with as_role(context, role):
        ids = [task["id"] for task in ok(context.api.get(url(context, TODO, "today/")))["results"]]
    assert context.saved[f"{alias}.task"] in ids, f"today of {role}: {ids}"


@when('the task of the company "{alias}" is done with the outcome "{outcome}"')
def step_task_done(context, alias, outcome):
    path = f"tasks/{context.saved[f'{alias}.task']}/done/"
    ok(context.api.post(url(context, TODO, path), json={"outcome": outcome}))


@when("the due reminder has run")
def step_remind(context):
    assert "REMINDED" in service_shell(REMIND)


def notifications(context, role: str) -> list[dict]:
    with as_role(context, role):
        response = context.api.get(url(context, NOTIFICATIONS, "notifications/"), params={"page_size": 100})
    return ok(response)["results"]


def reply_alerts(context, role: str, alias: str) -> list[dict]:
    """The leads alert of a reply ("Reply from <company>"); communicator's own reply alert goes to the role."""
    ref, title = f"leads.Company:{context.saved[alias]}", f"Reply from {context.saved[f'{alias}.name']}"
    return [row for row in notifications(context, role) if row["subject_ref"] == ref and row["title"] == title]


def read_all(context, role: str) -> None:
    """An alert only its owner sees stays unread for everyone else's `read-all/` and would escalate later."""
    with as_role(context, role):
        response = context.api.post(url(context, NOTIFICATIONS, "notifications/read-all/"), json={})
    ok(response)


@then('the {role} staff user has the reply alert about the company "{alias}"')
def step_notified(context, role, alias):
    context.add_cleanup(read_all, context, role)
    found = poll(lambda: reply_alerts(context, role, alias))
    assert found, f"no reply alert about {context.saved[alias]} for {role}"


@then('the {role} staff user has no reply alert about the company "{alias}"')
def step_not_notified(context, role, alias):
    found = reply_alerts(context, role, alias)
    assert not found, f"{role} sees {found}"


@then('the {role} staff user has a notification about the task of the company "{alias}"')
def step_task_bell(context, role, alias):
    ref = f"leads.Company:{context.saved[alias]}"
    found = [
        row for row in notifications(context, role) if row["subject_ref"] == ref and row["title"].startswith("Due")
    ]
    assert len(found) == 1 and not found[0]["escalate"], f"bell of {role}: {found}"


# --- Mail written by hand ---


@when('a mail "{subject}" is written by hand to the contact of "{alias}"')
def step_compose(context, alias, subject):
    body = {"contact_id": context.saved[f"{alias}.contact"], "subject": subject, "body": "Hello, a few words by hand."}
    context.response = context.api.post(url(context, LEADS, f"companies/{context.saved[alias]}/compose/"), json=body)
    context.response_data = context.response.json()


def cancel_open(context, subject_ref: str) -> None:
    params = {"subject_ref": subject_ref, "status": "open", "page_size": 100}
    for task in ok(context.api.get(url(context, TODO, "tasks/"), params=params))["results"]:
        ok(context.api.post(url(context, TODO, f"tasks/{task['id']}/cancel/"), json={"reason": "bdd cleanup"}))


@given('the open tasks about "{subject_ref}" are cancelled when the scenario ends')
def step_cancel_later(context, subject_ref):
    """Registered now, resolved at the end: no run fills the caller's today list."""
    context.add_cleanup(lambda: cancel_open(context, subject_ref.replace("{run}", str(context.saved["run"]))))
