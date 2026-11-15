# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CRM history steps (U5, U6, U11): cancelled tasks with reason and author, the company list with the caller's
companies first, the channel history and its filters, a settings change in the history."""

from __future__ import annotations

from datetime import date, timedelta

from behave import then, when

from entirius_tests.crm import LEADS, TODO, as_role, ok, poll, url


def history(context, **params) -> list[dict]:
    return ok(context.api.get(url(context, LEADS, "activities/"), params={"page_size": 100, **params}))["results"]


@when('the {role} staff user cancels the task of the company "{alias}" with the reason "{reason}"')
def step_cancel_task(context, role, alias, reason):
    with as_role(context, role):
        path = f"tasks/{context.saved[f'{alias}.task']}/cancel/"
        ok(context.api.post(url(context, TODO, path), json={"reason": reason}))


@then('the history entry "{event}" of the company "{alias}" has the reason "{reason}" by the {role} staff user')
def step_entry_reason(context, event, alias, reason, role):
    username = context.staff_users[role][0]

    def found():
        rows = history(context, company=context.saved[alias], kind="task")
        return [row for row in rows if row["data"].get("event") == event]

    assert poll(found), f"no {event} entry for company {context.saved[alias]}"
    entry = found()[0]
    assert (entry["data"].get("reason"), entry["actor"]) == (reason, username), entry


@then('the task of the company "{alias}" is in the cancelled tasks of the {role} staff user with the reason "{reason}"')
def step_cancelled_list(context, alias, role, reason):
    username = context.staff_users[role][0]
    with as_role(context, role):
        params = {
            "owner": "me",
            "status": "cancelled",
            "subject_ref": f"leads.Company:{context.saved[alias]}",
            "page_size": 100,
        }
        rows = ok(context.api.get(url(context, TODO, "tasks/"), params=params))["results"]
    task = next((row for row in rows if row["id"] == context.saved[f"{alias}.task"]), None)
    assert task, f"task {context.saved[f'{alias}.task']} not in the cancelled list of {role}"
    assert (task["outcome"], task["done_by"]) == (reason, username), task


@then('the {role} staff user\'s company list with "mine first" starts with their own companies')
def step_mine_first(context, role):
    username = context.staff_users[role][0]
    with as_role(context, role):
        params = {"mine_first": "true", "page_size": 100}
        rows = ok(context.api.get(url(context, LEADS, "companies/"), params=params))["results"]
    mine = [(row.get("owner") or {}).get("username") == username for row in rows]
    assert mine and mine[0], f"first company of {role}: {rows[:1]}"
    assert mine == sorted(mine, reverse=True), f"own companies not first: {mine}"


@then('the history of today filtered by the {role} staff user and the kind "{kind}" names the company "{alias}"')
def step_history_today(context, role, kind, alias):
    # yesterday to tomorrow: the server's day may differ from the runner's around midnight
    username, today = context.staff_users[role][0], date.today()
    days = {"date_from": (today - timedelta(days=1)).isoformat(), "date_to": (today + timedelta(days=1)).isoformat()}
    rows = history(context, actor=username, kind=kind, **days)
    assert rows, f"no {kind} entry of {username} today"

    # the person's filter takes their own actions and those through the AI CRM ("<username> via ai-crm (…)")
    def mine(actor):
        return actor == username or actor.startswith(f"{username} via ")

    assert all(mine(row["actor"]) and row["kind"] == kind for row in rows), rows[:3]
    assert any(row["company_id"] == context.saved[alias] and row["company_name"] for row in rows), rows[:3]


@then('the history filtered by the company "{alias}" has only entries of that company')
def step_history_company(context, alias):
    rows = history(context, company=context.saved[alias])
    assert rows and all(row["company_id"] == context.saved[alias] for row in rows), rows[:3]


@then("the {role} staff user is among the people of the history")
def step_history_actors(context, role):
    actors = ok(context.api.get(url(context, LEADS, "activities/actors/")))["results"]
    assert context.staff_users[role][0] in actors, actors


@when("the months the history is kept are changed for this scenario")
def step_change_months(context):
    channel_url = url(context, LEADS, "channel/")
    before = ok(context.api.get(channel_url))["history_months"]
    # earlier runs leave the same {"from": before, "to": after} entry: only an entry newer than this id counts
    context.saved["history_settings_seen"] = max((row["id"] for row in history(context, kind="settings")), default=0)
    after = 23 if before != 23 else 24
    context.add_cleanup(context.api.patch, channel_url, json={"history_months": before})
    ok(context.api.patch(channel_url, json={"history_months": after}))
    context.saved["history_months"] = (before, after)


@then("the history has a settings entry by the admin user with the old and the new months")
def step_settings_entry(context):
    before, after = context.saved["history_months"]
    rows = history(context, kind="settings", actor=context.admin_username)
    fresh = [row for row in rows if row["id"] > context.saved["history_settings_seen"]]
    changes = [row["data"]["changes"].get("history_months") for row in fresh]
    assert {"from": before, "to": after} in changes, f"no new settings entry with {before} -> {after}: {changes[:5]}"
    assert all(row["company_id"] is None for row in rows), rows[:3]
