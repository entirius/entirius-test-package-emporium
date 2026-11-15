# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI CRM steps (django-ai-crm, U10): the agent's day plan, the CMS conversation, the REST tools and the MCP server,
each as a seeded staff user with their own token. `{alias}` / `{alias.task}` in a message or a JSON body is the id
the scenario saved under that name."""

from __future__ import annotations

import json
import re

from behave import then, when

from entirius_tests.crm import LEADS, TODO, as_role, ok, poll, url

AI_CRM = "api/ai-crm/v2/admin/{channel}/"
DAY_ZONE = "UTC"  # both the plan and the today list count the day in this zone, whatever the server's TIME_ZONE
SAVED = re.compile(r"\{([\w.]+)\}")


def fill(context, text: str) -> str:
    return SAVED.sub(lambda match: str(context.saved[match.group(1)]), text)


def actor(context, role: str, source: str) -> str:
    return f"{context.staff_users[role][0]} via ai-crm ({source})"


def task(context, alias: str) -> dict:
    return ok(context.api.get(url(context, TODO, f"tasks/{context.saved[f'{alias}.task']}/")))


# --- Plan ---


@when("the {role} staff user asks the AI CRM agent for the day plan")
def step_plan(context, role):
    with as_role(context, role):
        context.saved["ai_crm.plan"] = ok(context.api.get(url(context, AI_CRM, "plan/"), params={"tz": DAY_ZONE}))


def plan_task_ids(context) -> list[int]:
    return [item["task_id"] for item in context.saved["ai_crm.plan"]["items"] if item["type"] == "task"]


@then('the AI CRM day plan lists the task of the company "{alias}"')
def step_plan_lists(context, alias):
    assert context.saved[f"{alias}.task"] in plan_task_ids(context), plan_task_ids(context)


@then('the AI CRM day plan does not list the task of the company "{alias}"')
def step_plan_lacks(context, alias):
    assert context.saved[f"{alias}.task"] not in plan_task_ids(context), plan_task_ids(context)


@then("the AI CRM day plan holds the same tasks as the today list of the {role} staff user")
def step_plan_is_today(context, role):
    with as_role(context, role):
        today_url = url(context, TODO, "today/")
        today = [row["id"] for row in ok(context.api.get(today_url, params={"tz": DAY_ZONE}))["results"]]
    assert plan_task_ids(context) == today, f"plan {plan_task_ids(context)} != today {today}"


# --- Conversation (the CMS screen) ---


@when('the {role} staff user says to the AI CRM agent from the CMS "{message}"')
def step_say(context, role, message):
    body = {"message": fill(context, message), "source": "cms", "language": "en"}
    with as_role(context, role):
        context.saved["ai_crm.turn"] = ok(context.api.post(url(context, AI_CRM, "chat/"), json=body))


@then("the AI CRM agent answered without a refusal")
def step_no_refusal(context):
    turn = context.saved["ai_crm.turn"]
    assert turn["results"] and all(result["status"] != "error" for result in turn["results"]), turn


@then("the AI CRM agent dropped the proposal")
def step_dropped(context):
    turn = context.saved["ai_crm.turn"]
    assert [result["status"] for result in turn["results"]] == ["rejected"], turn
    assert not turn["proposals"], turn


@then("the AI CRM agent proposes an action to confirm")
def step_proposes(context):
    turn = context.saved["ai_crm.turn"]
    assert [result["status"] for result in turn["results"]] == ["proposed"], turn
    assert turn["proposals"], turn


# --- Tools: REST and MCP ---


@when('the {role} staff user calls the AI CRM tool "{tool}" with')
def step_rest_tool(context, role, tool):
    body = {"arguments": json.loads(fill(context, context.text)), "source": "api"}
    with as_role(context, role):
        context.response = context.api.post(url(context, AI_CRM, f"tools/{tool}/"), json=body)


@then("the AI CRM tool refused for the missing permission")
def step_rest_refused(context):
    assert context.response.status_code == 403 and "is needed" in context.response.text, (
        f"{context.response.status_code}: {context.response.text[:300]}"
    )


@then("the AI CRM tool answered {status:d}")
def step_rest_status(context, status):
    assert context.response.status_code == status, f"{context.response.status_code}: {context.response.text[:300]}"


@when('the {role} staff user calls the AI CRM tool "{tool}" over MCP with')
def step_mcp_tool(context, role, tool):
    call = {"name": tool, "arguments": json.loads(fill(context, context.text))}
    with as_role(context, role):
        initialize = {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "bdd", "version": "1"},
        }
        ok(context.api.post(url(context, AI_CRM, "mcp/"), json=rpc("initialize", initialize)))
        answer = ok(context.api.post(url(context, AI_CRM, "mcp/"), json=rpc("tools/call", call)))
    assert "result" in answer, answer
    context.saved["ai_crm.mcp"] = answer["result"]


def rpc(method: str, params: dict) -> dict:
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}


@then("the MCP tool result is not an error")
def step_mcp_ok(context):
    result = context.saved["ai_crm.mcp"]
    assert result["isError"] is False, result


@then('the MCP tool result is the error "{code}"')
def step_mcp_error(context, code):
    result = context.saved["ai_crm.mcp"]
    assert result["isError"] is True and result["structuredContent"]["code"] == code, result


# --- What changed in the CRM ---


@then('the task of the company "{alias}" is done by the {role} staff user via ai-crm "{source}"')
def step_task_done_by(context, alias, role, source):
    row = task(context, alias)
    assert (row["status"], row["done_by"]) == ("done", actor(context, role, source)), row


@then('the task of the company "{alias}" is open')
def step_task_open(context, alias):
    row = task(context, alias)
    assert row["status"] == "open", f"task {row['id']} is {row['status']!r}, not open"


@then('the company "{alias}" has an activity "{kind}" by the {role} staff user via ai-crm "{source}"')
def step_activity_by(context, alias, kind, role, source):
    expected = actor(context, role, source)
    path = "activities/"
    params = {"company": context.saved[alias], "page_size": 100}

    def found():
        rows = ok(context.api.get(url(context, LEADS, path), params=params))["results"]
        return [row for row in rows if row["kind"] == kind and row["actor"] == expected]

    assert poll(found), f"no {kind} activity by {expected!r} for company {context.saved[alias]}"


@then('the deal is in the stage "{key}"')
def step_deal_stage(context, key):
    deal = ok(context.api.get(url(context, LEADS, f"deals/{context.saved['deal']}/")))
    assert deal["stage"]["key"] == key, deal["stage"]


@then("the deal is in an open stage")
def step_deal_open(context):
    deal = ok(context.api.get(url(context, LEADS, f"deals/{context.saved['deal']}/")))
    assert deal["stage"]["kind"] == "open", deal["stage"]


# `the company "{alias}" is not marked do not contact` lives in prospecting_steps.py (one definition per step).
