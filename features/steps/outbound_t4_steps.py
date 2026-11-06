# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps of the T4 scenarios (reply classes and next steps). They build on the T2a steps (`a fresh company is imported`,
`the company is contacted with the static mail`) and reply to the mail that left for the company. Nothing consumes the
seed; the settings a scenario changes are put back by cleanups."""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

from behave import given, then, when

from entirius_tests import clock, mail

LEADS = "api/leads/v2/admin/{channel}/"
COMMUNICATOR = "api/communicator/v2/admin/{channel}/"
NOTIFICATIONS = "api/notifications/v2/admin/{channel}/notifications/?role=sales_admin&page_size=100"
SUBJECT = "Re: BDD T4"


def _url(context, base: str, path: str = "") -> str:
    return context.api.url(base.format(channel=context.channel) + path)


def _json(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


def _sent(context, alias: str) -> dict:
    rows = _json(context.api.get(_url(context, COMMUNICATOR, "messages/?status=sent&page_size=100")))["results"]
    found = [m for m in rows if m["id"] == context.saved[f"{alias}.message"]]
    assert found, f"the mail to the company {alias} is not in the sent list"
    return found[0]


def _thread(context, alias: str) -> dict:
    ref = f"leads.Company:{context.saved[alias]}"
    threads = _json(context.api.get(_url(context, COMMUNICATOR, f"threads/?subject_ref={ref}")))["results"]
    assert threads, f"no thread about {ref}"
    return _json(context.api.get(_url(context, COMMUNICATOR, f"threads/{threads[0]['id']}/")))


def _last_reply(context, alias: str) -> dict:
    thread = _thread(context, alias)
    replies = _json(context.api.get(_url(context, COMMUNICATOR, f"replies/?thread={thread['id']}")))["results"]
    assert replies, f"the thread about the company {alias} has no reply"
    return replies[0]


def _with_dates(text: str) -> str:
    """`{in10}` = ten days after the reference Monday the channel clock stands on (ISO date)."""
    return re.sub(r"\{in(\d+)\}", lambda m: (clock.REFERENCE_MONDAY + timedelta(days=int(m[1]))).isoformat(), text)


@when('a reply with the text "{text}" arrives for the company "{alias}"')
def step_reply_arrives(context, text, alias):
    sent = _sent(context, alias)
    msg = EmailMessage()
    msg["From"] = f"Ewa <{context.saved[f'{alias}.email']}>"
    msg["To"] = "Outreach <sandbox@greenmail.test>"
    msg["Subject"] = SUBJECT
    # written a minute after our mail left (channel clock): the sender match ignores older mail
    msg["Date"] = format_datetime(datetime.fromisoformat(sent["sent_at"]) + timedelta(minutes=1))
    msg["Message-ID"] = make_msgid(idstring=f"bdd-t4-{time.time_ns()}", domain="inbound.test")
    msg["In-Reply-To"] = msg["References"] = sent["message_id"]
    msg.set_content(_with_dates(text))
    mail.append_raw(msg.as_bytes())


@then('the last reply about the company "{alias}" has kind "{kind}" and intent "{intent}"')
def step_reply_kind_intent(context, alias, kind, intent):
    reply = _last_reply(context, alias)
    assert (reply["kind"], reply["intent"]) == (kind, intent), f"reply: {reply['kind']} / {reply['intent']!r}"
    assert reply["intent_source"] == "toolbox" and reply["intent_confidence"], f"reply: {reply}"


@then('the last reply about the company "{alias}" has kind "{kind}" and no intent')
def step_reply_no_intent(context, alias, kind):
    reply = _last_reply(context, alias)
    assert (reply["kind"], reply["intent"], reply["intent_source"]) == (kind, "", ""), f"reply: {reply}"


@then('the last reply about the company "{alias}" has intent "{intent}"')
def step_reply_intent(context, alias, intent):
    assert _last_reply(context, alias)["intent"] == intent


@then('the last reply about the company "{alias}" has "{field}" set')
def step_reply_field_set(context, alias, field):
    reply = _last_reply(context, alias)
    assert field in reply and reply[field], f"{field} is empty in {reply}"


@then('the sequence about the company "{alias}" is stopped with reason "{reason}"')
def step_sequence_reason(context, alias, reason):
    state = _thread(context, alias)["sequence"]
    assert state and state["stopped_at"] and state["stop_reason"] == reason, f"sequence state: {state}"


@then('the sequence about the company "{alias}" is running')
def step_sequence_running(context, alias):
    thread = _thread(context, alias)
    state = thread["sequence"]
    assert state and not state["stopped_at"] and state["next_due_at"], f"sequence state: {state}"
    assert thread["status"] == "open", f"thread status {thread['status']!r}"


@when("the reply follow-ups have run")
def step_followups(context):
    response = context.api.post(_url(context, COMMUNICATOR, "test/reply-followups/"), json={})
    context.response_data = _json(response)


@then('the company "{alias}" got a "{severity}" notification titled "{title}"')
def step_notification(context, alias, severity, title):
    rows = _json(context.api.get(context.api.url(NOTIFICATIONS.format(channel=context.channel))))["results"]
    ref = f"leads.Company:{context.saved[alias]}"
    assert any(r["subject_ref"] == ref and r["severity"] == severity and title in r["title"] for r in rows), (
        f"no {severity} notification titled {title!r} for {ref}"
    )


@then('the contact of the company "{alias}" is flagged as the wrong person')
def step_contact_flagged(context, alias):
    detail = _json(context.api.get(_url(context, LEADS, f"companies/{context.saved[alias]}/")))
    contact = next(c for c in detail["contacts"] if c["email"] == context.saved[f"{alias}.email"])
    assert contact["wrong_person_at"], f"contact: {contact}"


@then('the replies flagged for review include the last reply about the company "{alias}"')
def step_flagged_list(context, alias):
    reply = _last_reply(context, alias)
    rows = _json(context.api.get(_url(context, COMMUNICATOR, "replies/?needs_review=true&page_size=100")))["results"]
    assert reply["id"] in [row["id"] for row in rows]


@when('I confirm the opt-out of the last reply about the company "{alias}"')
def step_confirm(context, alias):
    reply = _last_reply(context, alias)
    _json(context.api.post(_url(context, COMMUNICATOR, f"replies/{reply['id']}/confirm-optout/")))


def _suppressed(context) -> list[str]:
    return [
        r["value"]
        for r in _json(context.api.get(_url(context, COMMUNICATOR, "suppressions/?page_size=100")))["results"]
    ]


@then('the suppression list contains the address of the company "{alias}"')
def step_suppressed(context, alias):
    assert context.saved[f"{alias}.email"] in _suppressed(context)


@then('the suppression list does not contain the address of the company "{alias}"')
def step_not_suppressed(context, alias):
    assert context.saved[f"{alias}.email"] not in _suppressed(context)


def _put_action(context, intent: str, body: dict):
    url = _url(context, COMMUNICATOR, f"reply-actions/{intent}/")
    response = _json(context.api.put(url, json=body))
    context.add_cleanup(lambda: context.api.delete(url))
    return response


@given('the reply route of "{intent}" moves the company to the stage "{key}"')
def step_route_stage(context, intent, key):
    stages = _json(context.api.get(_url(context, LEADS, "stages/")))["results"]
    stage = next(s for s in stages if s["key"] == key)
    url = _url(context, LEADS, f"reply-routes/{intent}/")
    _json(context.api.put(url, json={"action": "stage", "stage_id": stage["id"]}))
    context.add_cleanup(lambda: context.api.delete(url))


@given('the reply action of "{intent}" asks for automatic suppression')
def step_auto_suppress(context, intent):
    _put_action(context, intent, {"auto_suppress": True})


@when('I set the reply action of "{intent}" to sequence "{sequence}" and notify "{notify}"')
def step_set_action(context, intent, sequence, notify):
    _put_action(context, intent, {"sequence": sequence, "notify": notify})


@when('I reset the reply action of "{intent}"')
def step_reset_action(context, intent):
    _json(context.api.delete(_url(context, COMMUNICATOR, f"reply-actions/{intent}/")))


def _action(context, intent: str) -> dict:
    rows = _json(context.api.get(_url(context, COMMUNICATOR, "reply-actions/")))["results"]
    return next(row for row in rows if row["intent"] == intent)


@then('the reply action of "{intent}" is sequence "{sequence}" and notify "{notify}" and is not the default')
def step_action_custom(context, intent, sequence, notify):
    row = _action(context, intent)
    assert (row["sequence"], row["notify"], row["is_default"]) == (sequence, notify, False), f"action: {row}"


@then('the reply action of "{intent}" is sequence "{sequence}" and notify "{notify}" and is the default')
def step_action_default(context, intent, sequence, notify):
    row = _action(context, intent)
    assert (row["sequence"], row["notify"], row["is_default"]) == (sequence, notify, True), f"action: {row}"
