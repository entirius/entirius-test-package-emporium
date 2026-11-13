# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CRM steps for mailboxes, their health, the approval inbox, one-click unsubscribe and the do-not-contact list.
Every change to a mailbox, the policy or the suppressions is put back when the scenario ends."""

from __future__ import annotations

import email
import re
import time
from datetime import datetime, timedelta
from email.utils import format_datetime
from pathlib import Path

from behave import given, then, when

from entirius_tests import clock, mail
from entirius_tests.crm import COMMUNICATOR, ok, poll, send_due, staff_id, url
from entirius_tests.stock_alerts import service_shell

APPROVALS = "api/communicator/v2/admin/approvals/"
UNSUBSCRIBE = "api/communicator/v2/public/unsubscribe/"
ONE_CLICK = {"List-Unsubscribe": "One-Click"}
TOKEN = re.compile(r"/unsubscribe/([^/>\s]+)/")
POLICY_FIELDS = ("enabled", "window_hours", "min_sample", "max_bounce_pct", "max_optout_pct", "max_complaint_pct")
MISSING_ID = 999_000_000
DSN_RECIPIENT = "owner@example-shop-6.test"
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."
CONTEXT = {"company_name": "Example Shop 1", "body": "BDD unsubscribe test."}
FORGET_RESET = """
from django_communicator.models import Mailbox
print("FORGOT", Mailbox.objects.filter(pk={pk}).update(health_reset_at=None))
"""
LIVE_CHECK = """
from django_communicator.models import Channel
from django_communicator.services import clock_service, health_service
channel = Channel.objects.get(idx={idx!r})
channel.mode = "live"
print("PAUSED", health_service.evaluate(channel, clock_service.now_for(channel)))
"""


def mailbox_of(context, role: str) -> dict:
    user_id = staff_id(context, role)
    rows = ok(context.api.get(url(context, COMMUNICATOR, "mailboxes/")))["results"]
    return next(row for row in rows if row["user_id"] == user_id)


def patch_mailbox(context, mailbox_id: int, body: dict) -> None:
    ok(context.api.patch(url(context, COMMUNICATOR, f"mailboxes/{mailbox_id}/"), json=body))


@given("the mailbox of the {role} staff user has a daily cap of {cap:d}")
def step_mailbox_cap(context, role, cap):
    box = mailbox_of(context, role)
    context.add_cleanup(patch_mailbox, context, box["id"], {"daily_cap": box["daily_cap"]})
    patch_mailbox(context, box["id"], {"daily_cap": cap})


def _resume(context, mailbox_id: int) -> None:
    """Resumes a paused mailbox; one that is not paused answers 409 and stays as it is."""
    response = context.api.post(url(context, COMMUNICATOR, f"mailboxes/{mailbox_id}/resume/"), json={"reason": "bdd"})
    assert response.status_code in (200, 409), f"resume: {response.status_code} {response.text[:200]}"


@given('the mailbox of the {role} staff user is paused with the reason "{reason}"')
@when('the mailbox of the {role} staff user is paused with the reason "{reason}"')
def step_mailbox_paused(context, role, reason):
    box = mailbox_of(context, role)
    context.add_cleanup(_resume, context, box["id"])
    ok(context.api.post(url(context, COMMUNICATOR, f"mailboxes/{box['id']}/pause/"), json={"reason": reason}))


def mailbox_health(context, role: str) -> dict:
    box_id = mailbox_of(context, role)["id"]
    report = ok(context.api.get(url(context, COMMUNICATOR, "health/")))
    return next(row for row in report["mailboxes"] if row["id"] == box_id)


@then('the health of the {role}\'s mailbox reports the state "{state}"')
def step_health_state(context, role, state):
    health = mailbox_health(context, role)
    assert health["state"] == state, f"health: {health}"


@then("the health of the {role}'s mailbox reports at least {count:d} mail sent today")
def step_health_sent(context, role, count):
    health = mailbox_health(context, role)
    assert health["sent_today"] >= count and health["windows"]["24h"]["sent"] >= count, f"health: {health}"


# --- Sandbox mail ---


def sandbox_mail(recipient: str, subject: str = "") -> email.message.Message:
    """The newest sandbox mail first addressed to `recipient` (and, given one, with `subject` in its subject)."""
    parsed = [email.message_from_string(row["mimeMessage"]) for row in mail.list_messages()]
    found = [m for m in parsed if m["X-Original-To"] == recipient and subject in str(m["Subject"] or "")]
    assert found, f"no sandbox mail to {recipient} {subject!r}"
    return found[-1]


def sender_of(message: email.message.Message) -> str:
    return email.utils.parseaddr(message["From"])[1]


@then('the sandbox mail to the contact of "{alias}" is from "{address}"')
def step_mail_from(context, alias, address):
    sender = sender_of(sandbox_mail(context.saved[f"{alias}.email"]))
    assert sender == address, f"From {sender}, expected {address}"


@then('the sandbox mail "{subject}" to the contact of "{alias}" is from "{address}"')
def step_subject_from(context, subject, alias, address):
    sender = sender_of(sandbox_mail(context.saved[f"{alias}.email"], subject))
    assert sender == address, f"From {sender}, expected {address}"


@given('an approved "{template_key}" message to a fresh address "{alias}" has been sent')
@when('an approved "{template_key}" message to a fresh address "{alias}" has been sent')
def step_fresh_address_sent(context, template_key, alias):
    """A unique address per run, unsuppressed again when the scenario ends; sent through the sandbox now."""
    address = context.saved[f"{alias}.email"] = f"bdd-crm-{time.time_ns()}@example-shop-1.test"
    context.add_cleanup(unsuppress, context, address)
    body = {"template_key": template_key, "subject_ref": f"bdd:crm:{address}", "requires_review": False}
    body |= {"recipient": {"email": address, "language": "pl", "legal_footer": LEGAL_FOOTER}, "context": CONTEXT}
    created = ok(context.api.post(url(context, COMMUNICATOR, "test/communicate/"), json=body), 201)
    send_due(context)
    sent = ok(context.api.get(url(context, COMMUNICATOR, f"review/{created['id']}/")))
    assert sent["sent_at"], f"message {created['id']} was not sent: {sent['status']}"
    context.saved |= {f"{alias}_thread": created["thread"]["id"], f"{alias}_message_id": sent["message_id"]}
    context.saved[f"{alias}_sent_at"] = datetime.fromisoformat(sent["sent_at"])


@then('the sandbox mail to the contact of "{alias}" carries the one-click unsubscribe headers')
def step_one_click_headers(context, alias):
    message = sandbox_mail(context.saved[f"{alias}.email"])
    assert message["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click", dict(message.items())
    assert TOKEN.search(message["List-Unsubscribe"] or ""), message["List-Unsubscribe"]


def unsubscribe_url(context, token: str) -> str:
    return context.api.url(f"{UNSUBSCRIBE}{token}/")


def link_token(context, alias: str) -> str:
    return TOKEN.search(sandbox_mail(context.saved[f"{alias}.email"])["List-Unsubscribe"]).group(1)


@when('the unsubscribe link of the sandbox mail to the contact of "{alias}" is opened')
def step_unsubscribe_open(context, alias):
    context.response = context.api.session.get(unsubscribe_url(context, link_token(context, alias)))


@when('the unsubscribe link of the sandbox mail to the contact of "{alias}" is posted as a one-click request')
def step_unsubscribe_post(context, alias):
    context.response = context.api.session.post(unsubscribe_url(context, link_token(context, alias)), data=ONE_CLICK)


@when('the unsubscribe link "{token}" is posted as a one-click request')
def step_unsubscribe_forged(context, token):
    context.response = context.api.session.post(unsubscribe_url(context, token), data=ONE_CLICK)


# --- Do-not-contact ---


def address_status(context, address: str) -> dict:
    return ok(context.api.get(url(context, COMMUNICATOR, "addresses/status/"), params={"email": address}))


@then('the address of "{alias}" is refused as "{refusal}"')
def step_address_refused(context, alias, refusal):
    status = address_status(context, context.saved[f"{alias}.email"])
    assert status["refusal"] == refusal, f"address status: {status}"


def unsuppress(context, address: str) -> None:
    rows = ok(context.api.get(url(context, COMMUNICATOR, "suppressions/"), params={"value": address}))["results"]
    for row in rows:
        ok(context.api.delete(url(context, COMMUNICATOR, f"suppressions/{row['id']}/")), 204)


@given('the address of "{alias}" is on the do-not-contact list of the channel')
def step_suppress(context, alias):
    address = context.saved[f"{alias}.email"]
    context.add_cleanup(unsuppress, context, address)
    body = {"kind": "email", "value": address, "reason": "bdd do not contact"}
    ok(context.api.post(url(context, COMMUNICATOR, "suppressions/"), json=body), 201)


# --- Approval inbox ---


@then('the approval inbox of the {role}\'s mailbox holds the draft of "{mine}" and not the draft of "{theirs}"')
def step_inbox_filter(context, role, mine, theirs):
    params = {"mailbox": mailbox_of(context, role)["id"], "page_size": 100, "search": context.saved[f"{mine}.email"]}
    ids = [row["id"] for row in ok(context.api.get(context.api.url(APPROVALS), params=params))["results"]]
    assert context.saved[f"{mine}.message"] in ids, f"approvals: {ids}"
    params["search"] = context.saved[f"{theirs}.email"]
    ids = [row["id"] for row in ok(context.api.get(context.api.url(APPROVALS), params=params))["results"]]
    assert context.saved[f"{theirs}.message"] not in ids, f"approvals: {ids}"


def bulk(context, body: dict) -> None:
    context.response = context.api.post(context.api.url(f"{APPROVALS}bulk/"), json=body)
    context.response_data = context.response.json()


@when('the drafts of "{alias}" and a missing message are approved in bulk')
def step_bulk_approve(context, alias):
    bulk(context, {"action": "approve", "ids": [context.saved[f"{alias}.message"], MISSING_ID], "reason": ""})


@then('the bulk answer lists the draft of "{alias}" as done and the missing message as failed')
def step_bulk_answer(context, alias):
    answer = ok(context.response)
    assert context.saved[f"{alias}.message"] in answer["done"], f"bulk: {answer}"
    assert str(MISSING_ID) in {str(key) for key in answer["failed"]}, f"bulk: {answer}"


@when('the draft of "{alias}" is rejected in bulk with the reason "{reason}"')
def step_bulk_reject(context, alias, reason):
    bulk(context, {"action": "reject", "ids": [context.saved[f"{alias}.message"]], "reason": reason})
    ok(context.response)


@when("{count:d} draft ids are approved in bulk")
def step_bulk_too_many(context, count):
    """Ids no message has: a regressed limit approves nothing."""
    bulk(context, {"action": "approve", "ids": list(range(MISSING_ID, MISSING_ID + count)), "reason": ""})


@then('the bulk approval log starts with a "{action}" entry')
def step_bulk_log(context, action):
    entries = ok(context.api.get(context.api.url(f"{APPROVALS}log/")))["results"]
    assert entries and entries[0]["action"] == action, f"log: {entries[:1]}"


def put_policy(context, body: dict) -> None:
    ok(context.api.put(url(context, COMMUNICATOR, "health/policy/"), json=body))


@given("the auto-pause policy is put back when the scenario ends")
def step_policy_cleanup(context):
    stored = ok(context.api.get(url(context, COMMUNICATOR, "health/policy/")))
    context.add_cleanup(put_policy, context, {key: stored[key] for key in POLICY_FIELDS})


@given("the auto-pause policy is enabled with a bounce limit of {limit:d} percent after {sample:d} mail")
def step_policy_strict(context, limit, sample):
    step_policy_cleanup(context)
    body = {"enabled": True, "window_hours": 24 * 90, "min_sample": sample, "max_bounce_pct": limit}
    put_policy(context, body | {"max_optout_pct": 3, "max_complaint_pct": 0.1})


def resume_and_forget(context, mailbox_id: int) -> None:
    """Resume, then drop the resume's health reset: it is stamped on the real clock, while the next run's mail is
    stamped on the reference-week channel clock, before it — the next health check would not see that mail."""
    _resume(context, mailbox_id)
    assert "FORGOT" in service_shell(FORGET_RESET.format(pk=mailbox_id))


@given("the mailbox of the {role} staff user is resumed when the scenario ends")
def step_resume_later(context, role):
    context.add_cleanup(resume_and_forget, context, mailbox_of(context, role)["id"])


@when("the health check of the channel in live mode has run")
def step_live_check(context):
    assert "PAUSED" in service_shell(LIVE_CHECK.format(idx=context.channel))


@then('the pause log starts with an automatic pause for "{trigger}"')
def step_pause_log(context, trigger):
    entries = ok(context.api.get(url(context, COMMUNICATOR, "health/log/")))["results"]
    assert entries and entries[0]["action"] == "pause" and entries[0]["trigger"] == trigger, f"log: {entries[:1]}"


@then('the do-not-contact entry of "{alias}" holds on the channel only')
def step_dnc_scope(context, alias):
    suppressions = context.response_data["communicator"]["suppressions"]
    assert suppressions and {row["scope"] for row in suppressions} == {"channel"}, f"suppressions: {suppressions}"


def _polled_reply(context, thread_id: int) -> bool:
    """One IMAP poll takes a batch: every sandbox copy sent earlier in the run waits in the same inbox before it."""
    ok(clock.run_imap_poll(context.api, context.channel))
    return bool(ok(context.api.get(url(context, COMMUNICATOR, "replies/"), params={"thread": thread_id}))["results"])


@when('the inbox is polled until the thread of "{alias}" has a reply')
def step_poll_until_reply(context, alias):
    assert poll(lambda: _polled_reply(context, context.saved[f"{alias}_thread"]), timeout=90), "no reply ingested"


@when('a hard bounce of the mail to the address of "{alias}" arrives')
def step_hard_bounce(context, alias):
    """`fixtures/mail/dsn_hard.eml` about the scenario's own mail and address, written a minute after it left."""
    path = Path(context.test_package_path).parent / "fixtures" / "mail" / "dsn_hard.eml"
    eml = mail.render_fixture(path, context.saved[f"{alias}_message_id"]).decode()
    eml = eml.replace(DSN_RECIPIENT, context.saved[f"{alias}.email"])
    eml = re.sub(r"^Message-ID: .*$", f"Message-ID: <bdd-{time.time_ns()}@inbound.test>", eml, count=1, flags=re.M)
    written = format_datetime(context.saved[f"{alias}_sent_at"] + timedelta(minutes=1))
    mail.append_raw(re.sub(r"^Date: .*$", f"Date: {written}", eml, count=1, flags=re.M).encode())
