# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads funnel steps (plan 12): every scenario finds its state again through the admin API, because saved values
do not survive between scenarios. Need `the channel is the primary channel` and an authenticated admin."""

from __future__ import annotations

import email
import time
from datetime import datetime

from behave import given, then

from entirius_tests import mail

COMMUNICATOR_ADMIN = "api/communicator/v2/admin/{channel}/"
NOTIFICATIONS_ADMIN = "api/notifications/v2/admin/{channel}/"


def _get(context, path: str) -> dict:
    response = context.api.get(context.api.url(path.format(channel=context.channel)))
    assert response.status_code == 200, f"GET {path}: {response.status_code} {response.text[:300]}"
    return response.json()


@then('the munin registry lists the modules "{names}"')
def step_registry_lists(context, names):
    modules = _get(context, "api/munin/v2/").get("modules", {})
    missing = [name.strip() for name in names.split(",") if name.strip() not in modules]
    assert not missing, f"munin registry misses {missing}"


def _threads(context, alias: str) -> list[dict]:
    ref = f"leads.Company:{context.saved[alias]}"
    return _get(context, f"{COMMUNICATOR_ADMIN}threads/?subject_ref={ref}&page_size=100")["results"]


@given('the review draft about the company "{alias}" is saved as "{message_alias}"')
def step_save_review_draft(context, alias, message_alias):
    ref = f"leads.Company:{context.saved[alias]}"
    rows = _get(context, f"{COMMUNICATOR_ADMIN}review/?page_size=100")["results"]
    drafts = [row for row in rows if row["thread"]["subject_ref"] == ref]
    assert len(drafts) == 1, f"expected one review draft about {ref}, found {len(drafts)}"
    context.saved[message_alias] = drafts[0]["id"]


@given('the sent message about the company "{alias}" is saved as "{message_alias}"')
def step_save_sent_message(context, alias, message_alias):
    """Saves what the communicator inbound steps expect: id, thread, subject_ref, Message-ID and sent_at."""
    thread_ids = {thread["id"] for thread in _threads(context, alias)}
    rows = _get(context, f"{COMMUNICATOR_ADMIN}messages/?status=sent&page_size=100")["results"]
    sent = [row for row in rows if row["thread"]["id"] in thread_ids]
    assert len(sent) == 1, f"expected one sent message about company {context.saved[alias]}, found {len(sent)}"
    context.saved.update(
        {
            message_alias: sent[0]["id"],
            f"{message_alias}_thread": sent[0]["thread"]["id"],
            f"{message_alias}_subject_ref": f"leads.Company:{context.saved[alias]}",
            f"{message_alias}_message_id": sent[0]["message_id"],
            f"{message_alias}_sent_at": datetime.fromisoformat(sent[0]["sent_at"]),
        }
    )


def _text_parts(message: email.message.Message) -> dict[str, str]:
    parts = [part for part in message.walk() if part.get_content_maintype() == "text"]
    return {
        part.get_content_type(): part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8")
        for part in parts
    }


@then('the sandbox message to "{recipient}" has a text and an html part containing "{text}"')
def step_mail_parts_contain(context, recipient, text):
    messages = [email.message_from_string(m["mimeMessage"]) for m in mail.list_messages()]
    matching = [m for m in messages if m["X-Original-To"] == recipient]
    assert matching, f"no sandbox message to {recipient}"
    parts = _text_parts(matching[-1])
    assert set(parts) >= {"text/plain", "text/html"}, f"parts: {sorted(parts)}"
    missing = [kind for kind, body in parts.items() if text not in body]
    assert not missing, f"{text!r} missing from {missing}"


@then("the notifications unread count is at least {n:d}")
def step_unread_at_least(context, n):
    unread = _get(context, f"{NOTIFICATIONS_ADMIN}notifications/unread-count/")["unread"]
    assert unread >= n, f"unread notifications: {unread}"


@then('the company "{alias}" has {count:d} hooks and a platform')
def step_company_hooks(context, alias, count):
    company = _get(context, f"api/leads/v2/admin/{{channel}}/companies/{context.saved[alias]}/")
    assert len(company["hooks"]) == count and company["platform"], (
        f"hooks {company['hooks']}, platform {company['platform']!r}"
    )


@then('the sandbox mailbox receives a message with the subject "{subject}"')
def step_mailbox_receives_subject(context, subject):
    """Escalation mail is sent by the worker; other unread alerts of the same seed may escalate too, so no count."""
    deadline = time.monotonic() + 20
    while subject not in (subjects := [m["subject"] for m in mail.list_messages()]) and time.monotonic() < deadline:
        time.sleep(0.5)
    assert subject in subjects, f"no sandbox message {subject!r}; subjects: {subjects}"
