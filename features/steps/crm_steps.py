# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CRM steps shared by the `@crm` features: a fresh imported company per scenario, a static mail sent through the
review queue and the sandbox, replies with a class through the development endpoint, tasks and mailboxes.

Need `the channel is the primary channel` and an authenticated staff user earlier in the scenario. Nothing here
consumes the seed: every company and address is unique per run, and every change to the channel configuration is put
back when the scenario ends."""

from __future__ import annotations

import io
import time
from datetime import UTC, datetime

from behave import given, then, when

from entirius_tests.crm import COMMUNICATOR, LEADS, TODO, ok, poll, send_due, staff_id, url

WORKER_TIMEOUT_S = 300
HEADER = "company_name,domain,website,lead_type,industry,first_name,last_name,email,job_title,language,legal_basis"


def subject_ref(context, alias: str) -> str:
    return f"leads.Company:{context.saved[alias]}"


# --- A fresh company per scenario ---


def upload(context, csv: str, form: dict[str, str]) -> None:
    """`test/import-now/` imports in the request but takes the file only; form fields (`run_rules`) go through
    `imports/` and the worker, which may still drain the seed's tasks right after `make seed`."""
    files = {"file": ("bdd-crm.csv", io.BytesIO(csv.encode()), "text/csv")}
    if not form:
        batch = ok(context.api.post(url(context, LEADS, "test/import-now/"), files=files))
        assert batch["status"] == "done", f"import: {batch}"
        context.saved["import_batch"] = batch
        return
    batch = ok(context.api.post(url(context, LEADS, "imports/"), files=files, data=form), 202)
    finished = {"done", "failed"}
    status = poll(
        lambda: (s := ok(context.api.get(url(context, LEADS, f"imports/{batch['id']}/")))["status"]) in finished and s,
        timeout=WORKER_TIMEOUT_S,
    )
    assert status == "done", f"import batch {batch['id']}: {status or 'not finished'}"


def import_fresh(context, alias: str, columns: dict[str, str], form: dict[str, str]) -> None:
    """One CSV row with a unique domain and address; saves the company id as `alias`, its address as
    `<alias>.email`, its domain as `<alias>.domain` and its contact id as `<alias>.contact`."""
    token = time.time_ns()
    domain, address = f"bdd-{token}.test", f"owner@bdd-{token}.test"
    row = f"BDD {token},{domain},,RETAILER,garden,Ewa,Nowak,{address},Owner,pl,legitimate_interest"
    header, row = ",".join([HEADER, *columns]), ",".join([row, *columns.values()])
    upload(context, f"{header}\n{row}\n", form)
    found = ok(context.api.get(url(context, LEADS, "companies/"), params={"search": domain}))["results"]
    assert len(found) == 1, f"expected one company {domain}, found {len(found)}"
    detail = ok(context.api.get(url(context, LEADS, f"companies/{found[0]['id']}/")))
    context.saved |= {alias: found[0]["id"], f"{alias}.email": address, f"{alias}.domain": domain}
    context.saved[f"{alias}.name"] = found[0]["name"]
    context.saved[f"{alias}.contact"] = detail["contacts"][0]["id"]
    context.add_cleanup(cancel_open_tasks, context, alias)


def cancel_open_tasks(context, alias: str) -> None:
    """Tasks about the scenario's company (replies, manual) are cancelled: no run fills a today list."""
    for task in open_tasks(context, alias):
        ok(context.api.post(url(context, TODO, f"tasks/{task['id']}/cancel/"), json={"reason": "bdd cleanup"}))


@given('a fresh company is imported as "{alias}"')
@when('a fresh company is imported as "{alias}"')
def step_fresh_company(context, alias):
    import_fresh(context, alias, {}, {})


@when('a fresh company is imported as "{alias}" with the rules on')
def step_fresh_company_rules(context, alias):
    import_fresh(context, alias, {}, {"run_rules": "true"})


@given('a fresh company is imported as "{alias}" with the columns')
@when('a fresh company is imported as "{alias}" with the columns')
def step_fresh_company_columns(context, alias):
    """Extra CSV columns from a `| column | value |` table; a value `{unique}` is made unique per run."""
    token = str(time.time_ns())
    columns = {row["column"]: row["value"].replace("{unique}", token) for row in context.table}
    import_fresh(context, alias, columns, {})
    context.saved |= {f"{alias}.{name}": value for name, value in columns.items()}


@then('the import report names the ignored column "{column}"')
def step_ignored_column(context, column):
    batch = context.saved["import_batch"]
    assert column in batch["ignored_columns"], f"ignored columns: {batch['ignored_columns']}"
    assert batch["automation_started_count"] == 0, f"automation started: {batch['automation_started_count']}"


@given('a fresh company owned by the {role} staff user is imported as "{alias}"')
def step_fresh_company_owned(context, role, alias):
    """Imported in the request, then given its owner (the import's `owner_id` would need the worker)."""
    import_fresh(context, alias, {}, {})
    body = {"owner_id": staff_id(context, role)}
    ok(context.api.patch(url(context, LEADS, f"companies/{context.saved[alias]}/"), json=body))


# --- Outbound mail of a company ---


def draft(context, alias: str, template_key: str) -> int:
    body = {"template_key": template_key, "contact_id": context.saved[f"{alias}.contact"]}
    path = f"companies/{context.saved[alias]}/communicate/"
    return ok(context.api.post(url(context, LEADS, path), json=body), 201)["message_id"]


def accept(context, message_id: int) -> None:
    ok(context.api.post(url(context, COMMUNICATOR, f"review/{message_id}/accept/"), json={}))


def skip_if_waiting(context, message_id: int) -> None:
    """A draft the scenario left for review is skipped, so the review queue holds no leftovers of a run."""
    if context.api.get(url(context, COMMUNICATOR, f"review/{message_id}/")).json().get("status") == "review_required":
        context.api.post(url(context, COMMUNICATOR, f"review/{message_id}/skip/"), json={})


@when('the company "{alias}" gets a draft of the static mail "{template_key}"')
def step_draft_only(context, alias, template_key):
    context.saved[f"{alias}.message"] = message_id = draft(context, alias, template_key)
    context.add_cleanup(skip_if_waiting, context, message_id)


@when('the company "{alias}" is approved for the static mail "{template_key}"')
def step_approved(context, alias, template_key):
    context.saved[f"{alias}.message"] = message_id = draft(context, alias, template_key)
    accept(context, message_id)


@when('the company "{alias}" is contacted with the static mail "{template_key}"')
@given('the company "{alias}" is contacted with the static mail "{template_key}"')
def step_contacted(context, alias, template_key):
    """Draft through the company's communicate endpoint, accept it in the review queue, run the send beat."""
    step_approved(context, alias, template_key)
    send_due(context)
    step_message_status(context, alias, "sent")


def message(context, alias: str) -> dict:
    return ok(context.api.get(url(context, COMMUNICATOR, f"review/{context.saved[f'{alias}.message']}/")))


@then('the mail of the company "{alias}" has status "{status}"')
def step_message_status(context, alias, status):
    actual = message(context, alias)["status"]
    assert actual == status, f"message {context.saved[f'{alias}.message']} is {actual}, expected {status}"


def thread(context, alias: str) -> dict:
    ref = subject_ref(context, alias)
    rows = ok(context.api.get(url(context, COMMUNICATOR, "threads/"), params={"subject_ref": ref}))["results"]
    assert rows, f"no thread about {ref}"
    return ok(context.api.get(url(context, COMMUNICATOR, f"threads/{rows[0]['id']}/")))


def sequence_id(context, key: str) -> int:
    rows = ok(context.api.get(url(context, COMMUNICATOR, "sequences/")))["results"]
    return next(row["id"] for row in rows if row["key"] == key)


def set_autostart(context, sequence: int, value: bool) -> None:
    ok(context.api.patch(url(context, COMMUNICATOR, f"sequences/{sequence}/"), json={"autostart": value}))


@given('the sequence "{key}" is the autostart sequence of the channel')
def step_autostart(context, key):
    """Off again when the scenario ends: a channel-wide autostart would give every other feature's first mail a
    follow-up sequence."""
    sequence = sequence_id(context, key)
    context.add_cleanup(set_autostart, context, sequence, False)
    set_autostart(context, sequence, True)


def sequence_state(context, alias: str, holds) -> dict:
    """The thread's sequence state once `holds(state)`; a delivery by the stack's own beat starts it a moment later."""
    state = poll(lambda: (lambda found: found if holds(found) else None)(thread(context, alias).get("sequence") or {}))
    return state or thread(context, alias).get("sequence") or {}


@then('the thread of the company "{alias}" runs the sequence "{key}" with a follow-up due')
def step_sequence_running(context, alias, key):
    expected = sequence_id(context, key)
    state = sequence_state(context, alias, lambda found: found.get("sequence_id") == expected and found["next_due_at"])
    assert state.get("sequence_id") == expected, f"sequence state: {state}"
    assert not state["stopped_at"] and state["next_due_at"], f"sequence is not running: {state}"


@then('the sequence of the company "{alias}" is stopped with reason "{reason}"')
def step_sequence_stopped(context, alias, reason):
    state = sequence_state(context, alias, lambda found: found.get("stop_reason") == reason)
    assert state.get("stopped_at") and state.get("stop_reason") == reason, f"sequence state: {state}"


# --- Replies with a class (development endpoint, no toolbox) ---


def ingest(context, alias: str, body: dict) -> None:
    body = {"thread_id": thread(context, alias)["id"], **body}
    reply = ok(context.api.post(url(context, COMMUNICATOR, "test/ingest-reply/"), json=body), 201)
    context.saved[f"{alias}.reply"] = reply["id"]


@when('the contact of "{alias}" replies "{text}" with the class "{intent}"')
def step_reply_class(context, alias, text, intent):
    ingest(context, alias, {"body": text, "intent": intent, "confidence": 0.95})


@when('the contact of "{alias}" replies "{text}" with the class "{intent}" back on {return_date}')
def step_reply_class_return(context, alias, text, intent, return_date):
    ingest(context, alias, {"body": text, "intent": intent, "confidence": 0.95, "return_date": return_date})


@when('the contact of "{alias}" replies "{text}" without a class')
def step_reply_plain(context, alias, text):
    ingest(context, alias, {"body": text})


def last_reply(context, alias: str) -> dict:
    replies = ok(
        context.api.get(url(context, COMMUNICATOR, "replies/"), params={"thread": thread(context, alias)["id"]})
    )
    return replies["results"][0]


@then('the last reply about the company "{alias}" has the kind "{kind}"')
def step_reply_kind(context, alias, kind):
    reply = last_reply(context, alias)
    assert reply["kind"] == kind, f"reply: {reply}"


@then('the last reply about the company "{alias}" needs review')
def step_reply_review(context, alias):
    reply = last_reply(context, alias)
    assert reply["needs_review"], f"reply: {reply}"


@then('the contact of "{alias}" is marked as the wrong person')
def step_wrong_person(context, alias):
    contact = ok(context.api.get(url(context, LEADS, f"contacts/{context.saved[f'{alias}.contact']}/")))
    assert contact["wrong_person_at"], f"contact: {contact}"


# --- Tasks ---


def open_tasks(context, alias: str) -> list[dict]:
    params = {"subject_ref": subject_ref(context, alias), "status": "open"}
    return ok(context.api.get(url(context, TODO, "tasks/"), params=params))["results"]


@then('the company "{alias}" has an open task "{title}"')
def step_open_task(context, alias, title):
    tasks = poll(lambda: [task for task in open_tasks(context, alias) if task["title"].startswith(title)])
    assert tasks, f"no open task {title!r}: {open_tasks(context, alias)}"
    context.saved[f"{alias}.task"] = tasks[0]["id"]
    context.saved[f"{alias}.task_title"] = tasks[0]["title"]


@then('the company "{alias}" has no open task')
def step_no_open_task(context, alias):
    """The development reply endpoint creates the task before it answers: nothing to wait for."""
    assert not open_tasks(context, alias), f"open tasks: {open_tasks(context, alias)}"


@then('the task of the company "{alias}" is due in {days:d} days')
def step_task_due(context, alias, days):
    task = ok(context.api.get(url(context, TODO, f"tasks/{context.saved[f'{alias}.task']}/")))
    due = datetime.fromisoformat(task["due_at"])
    delta = (due - datetime.now(UTC)).total_seconds() / 86400
    assert abs(delta - days) < 1, f"task due {task['due_at']}, expected in {days} days"
