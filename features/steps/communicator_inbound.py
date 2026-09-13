# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Communicator inbound steps: a sent sandbox message, fixture replies over IMAP, poll, reply/thread checks.
Need `the channel is the primary channel`, an authenticated admin and a sandbox channel earlier in the scenario.

Every scenario writes to a fresh thread, and every injected mail gets a fresh Message-ID, so a re-run on the
same seed never hits the inbound idempotency key of an earlier run."""

from __future__ import annotations

import re
import time
from pathlib import Path

from behave import given, then, when

from entirius_tests import clock, mail

ADMIN_PATH = "api/communicator/v2/admin/{channel_idx}/"
NOTIFICATIONS_PATH = "api/notifications/v2/admin/{channel_idx}/notifications/?role=sales_admin&page_size=100"
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."
MESSAGE_ID_HEADER = re.compile(rb"^Message-ID: .*$", re.MULTILINE)


def _url(context, path: str) -> str:
    return context.api.url(ADMIN_PATH.format(channel_idx=context.channel) + path)


def _ok(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text}"
    return response.json() if response.content else None


def _unsuppress(context, email: str) -> None:
    """An earlier run of a bounce/opt-out scenario suppressed this address; sending needs it cleared."""
    rows = _ok(context.api.get(_url(context, "suppressions/")))["results"]
    for row in rows:
        if row["value"] == email:
            _ok(context.api.delete(_url(context, f"suppressions/{row['id']}/")), 204)


def _sent_message(context, message_id: int) -> dict:
    url = _url(context, "messages/?status=sent&page_size=100")
    while url:
        page = _ok(context.api.get(url))
        found = [m for m in page["results"] if m["id"] == message_id]
        if found:
            return found[0]
        url = page["next"]
    raise AssertionError(f"message {message_id} was not sent")


@given('a sandbox message to "{email}" has been sent as "{alias}"')
def step_sent_message(context, email, alias):
    _unsuppress(context, email)
    body = {
        "template_key": "followup",
        "recipient": {"email": email, "first_name": "Anna", "language": "pl", "legal_footer": LEGAL_FOOTER},
        "context": {"company_name": "Example Shop", "body": "BDD inbound test."},
        "subject_ref": f"bdd:inbound:{time.time_ns()}",
        "requires_review": False,
    }
    created = _ok(context.api.post(_url(context, "test/communicate/"), json=body), 201)
    _ok(clock.run_beat_send(context.api, context.channel))
    context.saved[alias] = created["id"]
    context.saved[f"{alias}_thread"] = created["thread"]["id"]
    context.saved[f"{alias}_subject_ref"] = body["subject_ref"]
    context.saved[f"{alias}_message_id"] = _sent_message(context, created["id"])["message_id"]


@when('the fixture mail "{name}" arrives replying to "{alias}"')
def step_mail_arrives(context, name, alias):
    path = Path(context.test_package_path).parent / "fixtures" / "mail" / name
    assert path.is_file(), f"mail fixture not found: {path}"
    eml = mail.render_fixture(path, context.saved[f"{alias}_message_id"])
    fresh_id = f"Message-ID: <bdd-{time.time_ns()}@inbound.test>".encode()
    mail.append_raw(MESSAGE_ID_HEADER.sub(lambda _: fresh_id, eml, count=1))


@when("the communicator inbox has been polled")
def step_poll(context):
    context.response_data = _ok(clock.run_imap_poll(context.api, context.channel))


def _last_reply(context, alias: str) -> dict:
    thread_id = context.saved[f"{alias}_thread"]
    replies = _ok(context.api.get(_url(context, f"replies/?thread={thread_id}")))["results"]
    assert replies, f"thread {thread_id} has no reply"
    return replies[0]


@then('the thread of "{alias}" has status "{status}"')
def step_thread_status(context, alias, status):
    thread = _ok(context.api.get(_url(context, f"threads/{context.saved[f'{alias}_thread']}/")))
    assert thread["status"] == status, f"thread status {thread['status']!r}"


@then('the last reply in the thread of "{alias}" has kind "{kind}" matched by "{matched_by}"')
def step_reply_kind(context, alias, kind, matched_by):
    reply = _last_reply(context, alias)
    assert (reply["kind"], reply["matched_by"]) == (kind, matched_by), f"reply {reply['kind']} / {reply['matched_by']}"


@then('the thread of "{alias}" has {count:d} "{severity}" notifications')
def step_notifications(context, alias, count, severity):
    url = context.api.url(NOTIFICATIONS_PATH.format(channel_idx=context.channel))
    rows = _ok(context.api.get(url))["results"]
    ref = context.saved[f"{alias}_subject_ref"]
    actual = [row for row in rows if row["subject_ref"] == ref and row["severity"] == severity]
    assert len(actual) == count, f"expected {count} {severity} notifications for {ref}, found {len(actual)}"


@when('I confirm the opt-out of the last reply in the thread of "{alias}"')
def step_confirm_optout(context, alias):
    reply = _last_reply(context, alias)
    _ok(context.api.post(_url(context, f"replies/{reply['id']}/confirm-optout/")))


@then('the suppression list contains "{value}"')
def step_suppression_listed(context, value):
    values = [row["value"] for row in _ok(context.api.get(_url(context, "suppressions/")))["results"]]
    assert value in values, f"{value} not suppressed: {values}"


@then('the outbound message "{alias}" failed with code "{code}"')
def step_message_failed(context, alias, code):
    url = _url(context, "messages/?status=failed&page_size=100")
    while url:
        page = _ok(context.api.get(url))
        found = [m for m in page["results"] if m["id"] == context.saved[alias]]
        if found:
            assert found[0]["failure_code"] == code, f"failure_code {found[0]['failure_code']!r}"
            return
        url = page["next"]
    raise AssertionError(f"message {context.saved[alias]} is not failed")
