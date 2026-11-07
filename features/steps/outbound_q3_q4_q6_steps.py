# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps of the Q3 (sender routes, per-mailbox cap and warm-up), Q4 (approval inbox) and Q6 (one-click unsubscribe)
scenarios. They build on the communicator send steps (`I create an approved ... message`, `the beat send task has run`,
sandbox mail checks). Each scenario removes the routes it made and puts the channel default back."""

from __future__ import annotations

import email
import re
import time

from behave import given, then, when

from entirius_tests import mail

ADMIN = "api/communicator/v2/admin/{channel}/"
APPROVALS = "api/communicator/v2/admin/approvals/"
PUBLIC = "api/communicator/v2/public/unsubscribe/{token}/"
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."
UNSUBSCRIBE_RE = re.compile(r"<(https?://[^>]+/api/communicator/v2/public/unsubscribe/[^>]+)>")


def _url(context, path: str = "") -> str:
    return context.api.url(ADMIN.format(channel=context.channel) + path)


def _ok(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


def _route_body(from_email: str, cc_email: str = "", **extra) -> dict:
    return {"from_email": from_email, "cc_email": cc_email, "name": "BDD", **extra}


def _create_route(context, key: str, body: dict) -> None:
    """Created once per scenario run; routes of an earlier failed run are replaced. Removed when the scenario ends."""
    _remove_route(context, key)
    _ok(context.api.post(_url(context, "routes/"), json={"key": key, **body}), 201)
    context.add_cleanup(_remove_route, context, key)


def _remove_route(context, key: str) -> None:
    channel = context.api.get(_url(context, "channel/")).json()
    if channel.get("default_sender_route") == key:
        context.api.patch(_url(context, "channel/"), json={"default_sender_route": ""})
    context.api.delete(_url(context, f"routes/{key}/"))


@given('the sender route "{key}" exists from "{from_email}" with copy to "{cc_email}"')
def step_route(context, key, from_email, cc_email):
    _create_route(context, key, _route_body(from_email, cc_email))


@given('the sender route "{key}" exists with its own fresh mailbox and a daily cap of {cap:d}')
def step_route_cap(context, key, cap):
    """A mailbox address no earlier run has counted, so the per-mailbox counter starts at zero."""
    _create_route(context, key, _route_body(f"bdd-{time.time_ns()}@ecom.example.test", daily_cap=cap))


@given('the sender route "{key}" exists with a warm-up from {start:d} a day by {step:d} up to {ceiling:d}')
def step_route_warmup(context, key, start, step, ceiling):
    body = _route_body(
        f"bdd-{time.time_ns()}@ecom.example.test", daily_cap=ceiling, warmup_start_cap=start, warmup_step=step
    )
    _create_route(context, key, body)


def _route(context, key: str) -> dict:
    return _ok(context.api.get(_url(context, f"routes/{key}/")))


@then('the sender routes list holds "{key}" with copy to "{cc_email}"')
def step_route_listed(context, key, cc_email):
    rows = {row["key"]: row for row in _ok(context.api.get(_url(context, "routes/")))["results"]}
    assert key in rows and rows[key]["cc_email"] == cc_email, f"routes: {sorted(rows)}"


@then('creating the sender route "{key}" again is refused with status {status:d}')
def step_route_duplicate(context, key, status):
    response = context.api.post(_url(context, "routes/"), json={"key": key, **_route_body("x@ecom.example.test")})
    assert response.status_code == status, f"{response.status_code} {response.text[:200]}"


@when('I make "{key}" the default route of the channel')
def step_make_default(context, key):
    _ok(context.api.patch(_url(context, "channel/"), json={"default_sender_route": key}))


@then('making "{key}" the default route of the channel is refused with status {status:d}')
def step_default_refused(context, key, status):
    response = context.api.patch(_url(context, "channel/"), json={"default_sender_route": key})
    assert response.status_code == status, f"{response.status_code} {response.text[:200]}"


@then('the channel default route is "{key}"')
def step_default_is(context, key):
    assert _ok(context.api.get(_url(context, "channel/")))["default_sender_route"] == key


@then('deleting the sender route "{key}" is refused with status {status:d}')
def step_delete_refused(context, key, status):
    response = context.api.delete(_url(context, f"routes/{key}/"))
    assert response.status_code == status, f"{response.status_code} {response.text[:200]}"


@then('the sender route "{key}" has a cap of {cap:d} today and a warm-up start date')
def step_route_cap_today(context, key, cap):
    route = _route(context, key)
    assert route["cap_today"] == cap and route["warmup_started_on"], route


@then('the send policy lists the mailbox of "{key}" with a cap of {cap:d} today')
def step_policy_mailbox(context, key, cap):
    policy = _ok(context.api.get(_url(context, "policy/")))
    rows = {row["route"]: row for row in policy["mailboxes"]}
    assert key in rows and rows[key]["cap_today"] == cap and rows[key]["warmup"], rows


def _communicate(context, template_key: str, address: str, route: str, *, review: bool, footer: str = LEGAL_FOOTER):
    body = {
        "template_key": template_key,
        "recipient": {"email": address, "first_name": "Jan", "language": "pl", "legal_footer": footer},
        "context": {"company_name": "Example Shop 1", "body": "BDD wiadomość testowa."},
        "subject_ref": f"bdd:q:{time.time_ns()}",
        "requires_review": review,
        "sender_route": route,
    }
    return context.api.post(_url(context, "test/communicate/"), json=body)


@when('I create a routed approved "{template_key}" message to "{address}" on the sender route "{route}" as "{alias}"')
def step_create_on_route(context, template_key, address, route, alias):
    data = _ok(_communicate(context, template_key, address, route, review=False), 201)
    assert data["status"] == "approved" and data["thread"]["sender_route"] == route, data
    context.saved[alias] = data["id"]


def _run_id(context) -> str:
    """One id per scenario run, put into every draft address so the inbox filter sees only this run's drafts."""
    if not getattr(context, "q4_run_id", None):
        context.q4_run_id = str(time.time_ns())
        context.q4_drafts = []
        context.add_cleanup(_reject_leftovers, context)
    return context.q4_run_id


def _reject_leftovers(context) -> None:
    """Drafts still waiting leave the shared inbox when the scenario ends."""
    ids = list(context.q4_drafts)
    if ids:
        context.api.post(context.api.url(APPROVALS + "bulk/"), json={"action": "reject", "ids": ids, "reason": "bdd"})


@when('I create a draft for review to "{address}" on the sender route "{route}" as "{alias}"')
def step_create_draft(context, address, route, alias):
    local, _, domain = address.partition("@")
    data = _ok(_communicate(context, "reply.thanks", f"{local}-{_run_id(context)}@{domain}", route, review=True), 201)
    assert data["status"] == "review_required", data
    context.saved[alias] = data["id"]
    context.q4_drafts.append(data["id"])


@when('I try to create a "{template_key}" message to "{address}" without a legal footer')
def step_without_footer(context, template_key, address):
    context.response = _communicate(context, template_key, address, "", review=False, footer="")


@then('the outbound message "{alias}" has failure code "{code}" mentioning "{text}"')
def step_failure_code(context, alias, code, text):
    url = _url(context, "messages/?status=failed&page_size=100")
    rows = _ok(context.api.get(url))["results"]
    found = [m for m in rows if m["id"] == context.saved[alias]]
    assert found, f"message {context.saved[alias]} is not in the failed list"
    assert found[0]["failure_code"] == code and text in found[0]["failure_detail"], found[0]


def _sandbox_mail(recipient: str) -> email.message.Message:
    parsed = [email.message_from_string(m["mimeMessage"]) for m in mail.list_messages()]
    found = [m for m in parsed if m["X-Original-To"] == recipient]
    assert found, f"no sandbox message to {recipient}"
    return found[-1]


@then('the sandbox message to "{recipient}" is from "{address}"')
def step_mail_from(context, recipient, address):
    sender = _sandbox_mail(recipient)["From"] or ""
    assert f"<{address}>" in sender or sender == address, f"From {sender!r}"


@then('the sandbox message to "{recipient}" has the header "{header}" equal to "{value}"')
def step_mail_header(context, recipient, header, value):
    assert _sandbox_mail(recipient)[header] == value, _sandbox_mail(recipient)[header]


@then('the sandbox message to "{recipient}" has no Cc')
def step_mail_no_cc(context, recipient):
    assert not _sandbox_mail(recipient)["Cc"], _sandbox_mail(recipient)["Cc"]


def _approvals(context, **query) -> dict:
    return _ok(context.api.get(context.api.url(APPROVALS), params={"page_size": 100, **query}))


@then("the approval inbox of this run holds {count:d} drafts")
def step_inbox_count(context, count):
    """The run id is in every draft address, so the search narrows the shared inbox to this scenario's drafts."""
    actual = _approvals(context, q=_run_id(context))["count"]
    assert actual == count, f"expected {count} drafts, the inbox holds {actual}"


@then('the approval inbox of this run on the route "{route}" holds {count:d} drafts')
def step_inbox_route(context, route, count):
    actual = _approvals(context, q=_run_id(context), sender_route=route)["count"]
    assert actual == count, f"expected {count} drafts on {route}, the inbox holds {actual}"


def _row(context, alias: str) -> dict:
    rows = _approvals(context)["results"]
    found = [row for row in rows if row["id"] == context.saved[alias]]
    assert found, f"draft {context.saved[alias]} is not in the approval inbox"
    return found[0]


@then('the approval inbox row of "{alias}" is from "{address}" with template "{template}" and no blocker')
def step_row_ok(context, alias, address, template):
    row = _row(context, alias)
    assert (row["sender_from"], row["template_key"], row["blocker"]) == (address, template, ""), row


@then('the approval inbox row of "{alias}" has a blocker mentioning "{text}"')
def step_row_blocker(context, alias, text):
    assert text in _row(context, alias)["blocker"], _row(context, alias)


def _bulk(context, action: str, ids: list[int], reason: str = ""):
    context.response = context.api.post(
        context.api.url(APPROVALS + "bulk/"), json={"action": action, "ids": ids, "reason": reason}
    )
    return context.response


def _ids(context, aliases: str) -> list[int]:
    return [context.saved[alias.strip()] for alias in aliases.split(",")]


@when('I bulk approve the drafts "{aliases}"')
def step_bulk_approve(context, aliases):
    context.bulk = _ok(_bulk(context, "approve", _ids(context, aliases)))
    context.bulk_batches = [context.bulk["id"]]


@when('I bulk reject the drafts "{aliases}" with the reason "{reason}"')
def step_bulk_reject(context, aliases, reason):
    batch = _ok(_bulk(context, "reject", _ids(context, aliases), reason))
    context.bulk_batches = [*getattr(context, "bulk_batches", []), batch["id"]]


@when("I bulk approve {count:d} draft ids")
def step_bulk_many(context, count):
    _bulk(context, "approve", list(range(900_000_000, 900_000_000 + count)))


@then('the bulk result lists "{done}" as done and "{failed}" as failed')
def step_bulk_result(context, done, failed):
    assert context.saved[done] in context.bulk["done"], context.bulk
    assert str(context.saved[failed]) in context.bulk["failed"], context.bulk


@then('the review message "{alias}" has status "{status}"')
def step_review_status(context, alias, status):
    message = _ok(context.api.get(_url(context, f"review/{context.saved[alias]}/")))
    assert message["status"] == status, message["status"]


@then("the bulk approval log has an entry of the admin user for each of the two batches")
def step_bulk_log(context):
    log = _ok(context.api.get(context.api.url(APPROVALS + "log/"), params={"page_size": 100}))["results"]
    entries = {row["id"]: row for row in log}
    assert all(batch in entries for batch in context.bulk_batches), (context.bulk_batches, sorted(entries))
    assert all(entries[batch]["user_id"] for batch in context.bulk_batches), entries


@then("the last response status is {status:d}")
def step_last_status(context, status):
    assert context.response.status_code == status, f"{context.response.status_code} {context.response.text[:200]}"


def _public(context, token: str):
    return context.api.url(PUBLIC.format(token=token))


@when('the unsubscribe link "{token}" is posted')
def step_post_token(context, token):
    context.response = context.api.post(_public(context, token))


@when('the unsubscribe link "{token}" is opened')
def step_open_token(context, token):
    context.response = context.api.get(_public(context, token))


def _link(context, recipient: str) -> str:
    """The List-Unsubscribe URL of the sandbox mail; the scenario skips itself while the stack has no base URL."""
    header = _sandbox_mail(recipient)["List-Unsubscribe"]
    if not header:
        context.scenario.skip("COMMUNICATOR_UNSUBSCRIBE_BASE_URL is not set in the stack")
        return ""
    found = UNSUBSCRIBE_RE.match(header.strip())
    assert found, f"List-Unsubscribe {header!r}"
    return found.group(1)


@then('the sandbox message to "{recipient}" has the one-click unsubscribe headers')
def step_mail_unsubscribe_headers(context, recipient):
    if not _link(context, recipient):
        return
    assert _sandbox_mail(recipient)["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


@when('the unsubscribe link of the sandbox message to "{recipient}" is opened')
def step_open_link(context, recipient):
    if link := _link(context, recipient):
        context.response = context.api.get(link)


@when('the unsubscribe link of the sandbox message to "{recipient}" is posted as a one-click request')
def step_post_link(context, recipient):
    if link := _link(context, recipient):
        context.add_cleanup(_unsuppress, context, recipient)
        context.response = context.api.post(
            link, data="List-Unsubscribe=One-Click", headers={"Content-Type": "application/x-www-form-urlencoded"}
        )


def _suppressed(context, address: str) -> bool:
    rows = _ok(context.api.get(_url(context, f"suppressions/?value={address}")))["results"]
    return any(row["value"] == address for row in rows)


def _unsuppress(context, address: str) -> None:
    """The suppression this scenario made is removed, so the scenario can run again with the same address."""
    rows = context.api.get(_url(context, f"suppressions/?value={address}")).json().get("results", [])
    for row in rows:
        if row["value"] == address and row["kind"] == "email":
            context.api.delete(_url(context, f"suppressions/{row['id']}/"))


@then('"{address}" is not suppressed yet')
def step_not_suppressed(context, address):
    assert not _suppressed(context, address)


@then('"{address}" is suppressed on the channel')
def step_suppressed(context, address):
    assert _suppressed(context, address)


@when('I create a "{template_key}" message to "{email_address}" as "{alias}" after the unsubscribe')
def step_create_after_unsubscribe(context, template_key, email_address, alias):
    """The communicator already refuses a suppressed address when the message is created: it is born `suppressed`."""
    body = {
        "template_key": template_key,
        "recipient": {"email": email_address, "first_name": "Jan", "language": "pl", "legal_footer": LEGAL_FOOTER},
        "context": {"company_name": "Example Shop 1", "body": "BDD wiadomość testowa."},
        "subject_ref": f"bdd:q6:{time.time_ns()}",
        "requires_review": False,
    }
    data = _ok(context.api.post(_url(context, "test/communicate/"), json=body), 201)
    context.saved[alias] = data["id"]
    assert data["status"] == "suppressed", data["status"]
