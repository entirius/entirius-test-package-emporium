# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Communicator sending steps: channel mode, approved messages on fresh threads, outbox and sandbox mail checks.
Need `the channel is the primary channel` and an authenticated admin earlier in the scenario."""

from __future__ import annotations

import email
import time
from datetime import datetime

from behave import given, then, when

from entirius_tests import clock, mail

ADMIN_PATH = "api/communicator/v2/admin/{channel_idx}/"
FIXTURE_MODE = "sandbox"
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."
CONTEXT = {"company_name": "Example Shop 1", "body": "BDD wiadomość testowa."}


def _url(context, path: str) -> str:
    return context.api.url(ADMIN_PATH.format(channel_idx=context.channel) + path)


def _set_mode(context, mode: str):
    return context.api.patch(_url(context, "channel/"), json={"mode": mode})


@given('the communicator channel is in "{mode}" mode')
def step_channel_mode(context, mode):
    """The fixture mode is restored when the scenario ends."""
    if not getattr(context, "communicator_mode_cleanup", False):
        context.add_cleanup(_set_mode, context, FIXTURE_MODE)
        context.communicator_mode_cleanup = True
    response = _set_mode(context, mode)
    assert response.status_code == 200, f"channel mode {mode}: {response.status_code} {response.text}"


@given("the beat has drained every due message")
def step_drain(context):
    """Delivers (or records, in dry_run) whatever earlier features left due at the current channel clock."""
    response = clock.run_beat_send(context.api, context.channel)
    assert response.status_code == 200, f"send-due: {response.status_code} {response.text}"


@given("the daily cap leaves room for {count:d} more messages today")
def step_cap_room(context, count):
    """Cap = today's counter (channel clock) + `count`; the original policy is put back when the scenario ends."""
    policy = context.api.get(_url(context, "policy/")).json()
    fields = ("business_days_only", "daily_cap", "spread")
    original = {name: policy[name] for name in fields}
    original["windows"] = [{k: w[k] for k in ("order", "start_time", "end_time")} for w in policy["windows"]]
    context.add_cleanup(context.api.put, _url(context, "policy/"), json=original)
    response = context.api.put(_url(context, "policy/"), json={**original, "daily_cap": policy["sent_today"] + count})
    assert response.status_code == 200, f"policy: {response.status_code} {response.text}"


def _create_approved(context, template_key: str, email_address: str) -> dict:
    """A static auto-approve message on a thread of its own (unique subject_ref)."""
    body = {
        "template_key": template_key,
        "recipient": {"email": email_address, "first_name": "Jan", "language": "pl", "legal_footer": LEGAL_FOOTER},
        "context": CONTEXT,
        "subject_ref": f"bdd:send:{time.time_ns()}",
        "requires_review": False,
    }
    response = context.api.post(_url(context, "test/communicate/"), json=body)
    assert response.status_code == 201, f"communicate: {response.status_code} {response.text}"
    data = response.json()
    assert data["status"] == "approved", f"expected an approved message, got {data['status']}"
    return data


@when('I create an approved "{template_key}" message to "{email_address}" as "{alias}"')
def step_create_approved(context, template_key, email_address, alias):
    data = _create_approved(context, template_key, email_address)
    context.saved[alias] = data["id"]
    context.saved[f"{alias}_thread"] = data["thread"]["id"]


@when('I create {count:d} approved "{template_key}" messages to "{email_address}"')
def step_create_many(context, count, template_key, email_address):
    for _ in range(count):
        _create_approved(context, template_key, email_address)


@when('I start the "{sequence_key}" sequence in the thread of "{alias}"')
def step_start_sequence(context, sequence_key, alias):
    body = {"thread_id": context.saved[f"{alias}_thread"], "sequence_key": sequence_key}
    response = context.api.post(_url(context, "test/start-sequence/"), json=body)
    assert response.status_code == 201, f"start-sequence: {response.status_code} {response.text}"


def _outbox_message(context, alias: str, status: str) -> dict | None:
    url = _url(context, f"messages/?status={status}&page_size=100")
    while url:
        page = context.api.get(url).json()
        found = [m for m in page["results"] if m["id"] == context.saved[alias]]
        if found:
            return found[0]
        url = page["next"]
    return None


@then('the outbound message "{alias}" has status "{status}"')
def step_outbox_status(context, alias, status):
    assert _outbox_message(context, alias, status), f"message {context.saved[alias]} is not {status}"


@then('the outbound message "{alias}" has its next slot on {weekday} at {hhmm}')
def step_next_slot(context, alias, weekday, hhmm):
    message = _outbox_message(context, alias, "approved")
    assert message and message["next_slot"], f"message {context.saved[alias]} has no next slot"
    slot = datetime.fromisoformat(message["next_slot"])
    assert (slot.strftime("%A").lower(), slot.strftime("%H:%M")) == (weekday.lower(), hhmm), f"next slot {slot}"


def _mail_to(recipient: str) -> list[email.message.Message]:
    """Sandbox mail originally addressed to `recipient`, oldest first."""
    parsed = [email.message_from_string(m["mimeMessage"]) for m in mail.list_messages()]
    return [m for m in parsed if m["X-Original-To"] == recipient]


@then('the sandbox mailbox holds {count:d} messages to "{recipient}"')
def step_mail_count(context, count, recipient):
    actual = len(_mail_to(recipient))
    assert actual == count, f"expected {count} sandbox messages to {recipient}, found {actual}"


def _last_to(recipient: str) -> email.message.Message:
    messages = _mail_to(recipient)
    assert messages, f"no sandbox message to {recipient}"
    return messages[-1]


@then('the sandbox message to "{recipient}" has a subject starting with "{prefix}"')
def step_mail_subject(context, recipient, prefix):
    subject = _last_to(recipient)["Subject"] or ""
    assert subject.startswith(prefix), f"subject {subject!r} does not start with {prefix!r}"


@then('the sandbox message to "{recipient}" is multipart/alternative with our Message-ID')
def step_mail_structure(context, recipient):
    message = _last_to(recipient)
    assert message.get_content_type() == "multipart/alternative", message.get_content_type()
    assert (message["Message-ID"] or "").startswith("<communicator-"), message["Message-ID"]


@then('the last sandbox message to "{recipient}" references the first one')
def step_mail_references(context, recipient):
    first, last = _mail_to(recipient)[0], _last_to(recipient)
    assert first["Message-ID"] in (last["References"] or ""), f"References {last['References']!r}"
    assert last["In-Reply-To"] == first["Message-ID"], f"In-Reply-To {last['In-Reply-To']!r}"
