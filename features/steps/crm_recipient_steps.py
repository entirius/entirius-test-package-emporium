# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The recipient check of a draft (one sentence in the approval list, on approval and in the bulk answer), drafts
nobody may send leaving the queue, rejected drafts on the timeline, the funnel's first stage and the mailbox login
test. Builds on the `@crm` steps of `crm_steps.py`; every change to a company is put back when the scenario ends."""

from __future__ import annotations

from datetime import datetime

from behave import then, when

from entirius_tests.crm import COMMUNICATOR, LEADS, ok, staff_id, url

APPROVALS = "api/communicator/v2/admin/approvals/"


def draft_id(context, alias: str) -> int:
    return context.saved[f"{alias}.message"]


def set_do_not_contact(context, alias: str, value: bool) -> None:
    body = {"do_not_contact": value}
    ok(context.api.patch(url(context, LEADS, f"companies/{context.saved[alias]}/"), json=body))


@when('the company "{alias}" is marked do not contact')
def step_mark_dnc(context, alias):
    context.add_cleanup(set_do_not_contact, context, alias, False)
    set_do_not_contact(context, alias, True)


@when('the do-not-contact mark of the company "{alias}" is lifted')
def step_lift_dnc(context, alias):
    set_do_not_contact(context, alias, False)


def set_legal_basis(context, alias: str, basis: str | None) -> None:
    path = f"contacts/{context.saved[f'{alias}.contact']}/"
    ok(context.api.patch(url(context, LEADS, path), json={"legal_basis": basis}))


@when('the contact of "{alias}" loses its legal basis')
def step_no_basis(context, alias):
    """Put back to the import's basis when the scenario ends (its draft is skipped by the draft step's cleanup)."""
    context.add_cleanup(set_legal_basis, context, alias, "legitimate_interest")
    set_legal_basis(context, alias, None)


@then('the approval row of the draft of "{alias}" is blocked with "{sentence}"')
def step_row_blocker(context, alias, sentence):
    params = {"search": context.saved[f"{alias}.email"], "page_size": 100}
    rows = ok(context.api.get(context.api.url(APPROVALS), params=params))["results"]
    row = next((row for row in rows if row["id"] == draft_id(context, alias)), None)
    assert row is not None, f"no approval row of {alias}: {[r['id'] for r in rows]}"
    assert row["blocker"] == sentence, f"blocker {row['blocker']!r}, expected {sentence!r}"


@then('approving the draft of "{alias}" is refused with "{sentence}"')
def step_single_refused(context, alias, sentence):
    response = context.api.post(url(context, COMMUNICATOR, f"review/{draft_id(context, alias)}/accept/"), json={})
    assert response.status_code == 409, f"accept: {response.status_code} {response.text[:300]}"
    assert response.json()["message"] == sentence, f"accept: {response.json()}"


@then('approving the draft of "{alias}" in bulk is refused with "{sentence}"')
def step_bulk_refused(context, alias, sentence):
    body = {"action": "approve", "ids": [draft_id(context, alias)], "reason": ""}
    answer = ok(context.api.post(context.api.url(f"{APPROVALS}bulk/"), json=body))
    assert answer["done"] == [] and answer["failed"] == {str(draft_id(context, alias)): sentence}, f"bulk: {answer}"


@then('approving the draft of "{alias}" succeeds')
def step_approved(context, alias):
    message = ok(context.api.post(url(context, COMMUNICATOR, f"review/{draft_id(context, alias)}/accept/"), json={}))
    assert message["status"] == "approved", f"accept: {message}"


@when('the draft of "{alias}" is skipped with the reason "{reason}"')
def step_skip(context, alias, reason):
    path = f"review/{draft_id(context, alias)}/skip/"
    ok(context.api.post(url(context, COMMUNICATOR, path), json={"reason": reason}))


@when('the suspected opt-out of "{alias}" is confirmed')
def step_confirm_optout(context, alias):
    path = f"replies/{context.saved[f'{alias}.reply']}/confirm-optout/"
    ok(context.api.post(url(context, COMMUNICATOR, path), json={}))


def rejected_entry(context, alias: str) -> dict:
    """The rejected draft's entry on the timeline of its own thread, dated by its rejection."""
    message = ok(context.api.get(url(context, COMMUNICATOR, f"review/{draft_id(context, alias)}/")))
    thread = ok(context.api.get(url(context, COMMUNICATOR, f"threads/{message['thread']['id']}/")))
    entry = next((e for e in thread["timeline"] if e["message_id"] == draft_id(context, alias)), None)
    assert entry is not None, f"draft {draft_id(context, alias)} is not on the timeline: {thread['timeline']}"
    rejected_at = datetime.fromisoformat(message["reviewed_at"])
    assert datetime.fromisoformat(entry["at"]) == rejected_at, f"not dated by its rejection: {entry}, {message}"
    return entry


@then('the timeline shows the draft of "{alias}" rejected by a person with the reason "{reason}"')
def step_rejected_by_person(context, alias, reason):
    entry = rejected_entry(context, alias)
    assert entry["status"] == "rejected" and entry["reject_reason"] == reason, f"entry: {entry}"
    assert entry["rejected_by"], f"no reviewer on a skipped draft: {entry}"


@then('the timeline shows the draft of "{alias}" withdrawn with the reason "{reason}"')
def step_withdrawn(context, alias, reason):
    entry = rejected_entry(context, alias)
    assert (entry["status"], entry["rejected_by"], entry["reject_reason"]) == ("rejected", "", reason), entry


@then('the funnel report of the origin of "{alias}" counts 1 company entered in the stage "{stage}"')
def step_funnel_entered(context, alias, stage):
    params = {"origin": context.saved[f"{alias}.origin"]}
    report = ok(context.api.get(url(context, LEADS, "reports/funnel/"), params=params))
    row = next(row for row in report["stages"] if row["key"] == stage)
    assert row["entered"] == 1, f"stage {stage}: {row}"


@then('the login test of the mailbox of the {role} staff user answers "ok" for SMTP and IMAP')
def step_login_test(context, role):
    user_id = staff_id(context, role)
    rows = ok(context.api.get(url(context, COMMUNICATOR, "mailboxes/")))["results"]
    mailbox = next(row for row in rows if row["user_id"] == user_id)
    answer = ok(context.api.post(url(context, COMMUNICATOR, f"mailboxes/{mailbox['id']}/test/"), json={}))
    assert answer == {"smtp": "ok", "imap": "ok"}, f"login test of {mailbox['address']}: {answer}"
