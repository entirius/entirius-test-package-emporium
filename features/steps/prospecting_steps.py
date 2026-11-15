# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""U3 steps (`features/leads/prospecting.feature`): the search for another person (django-prospecting), its
candidates and their four checks, accept / reject, and communicator's referral request.

Need the CRM steps (`crm_steps.py`) earlier in the scenario: a fresh company (`a fresh company is imported as`)."""

from __future__ import annotations

from behave import then, when

from entirius_tests.crm import COMMUNICATOR, LEADS, PROSPECTING, ok, poll, url

SEARCH_TIMEOUT_S = 120
LOOKING = "looking for another person"


def subject_ref(context, alias: str) -> str:
    return f"leads.Company:{context.saved[alias]}"


def finished_search(context, alias: str) -> dict:
    """The newest search of the company once the worker finished it."""

    def done():
        rows = ok(
            context.api.get(
                url(context, PROSPECTING, "people/searches/"), params={"subject_ref": subject_ref(context, alias)}
            )
        )
        return rows["results"][0] if rows["results"] and rows["results"][0]["status"] != "queued" else None

    search = poll(done, timeout=SEARCH_TIMEOUT_S)
    assert search, (
        f"no finished people search for {subject_ref(context, alias)} (is the worker consuming prospecting_default?)"
    )
    return search


def candidates(context, alias: str) -> list[dict]:
    finished_search(context, alias)
    params = {"subject_ref": subject_ref(context, alias)}
    return ok(context.api.get(url(context, PROSPECTING, "people/candidates/"), params=params))["results"]


def candidate(context, alias: str, last_name: str) -> dict:
    found = [row for row in candidates(context, alias) if row["last_name"] == last_name]
    assert len(found) == 1, f"candidate {last_name}: {found}"
    return found[0]


def checks(row: dict) -> dict[str, dict]:
    return {check["kind"]: check for check in row["checks"]}


def contacts(context, alias: str) -> list[dict]:
    params = {"company": context.saved[alias]}
    return ok(context.api.get(url(context, LEADS, "contacts/"), params=params))["results"]


# --- The search ---


@then('the history of the company "{alias}" says "{message}" for the reason "{reason}"')
def step_history(context, alias, message, reason):
    def found():
        params = {"company": context.saved[alias], "page_size": 100}
        rows = ok(context.api.get(url(context, LEADS, "activities/"), params=params))["results"]
        return [row for row in rows if row["message"] == message]

    rows = poll(found)
    assert rows, f"no '{message}' in the history of {alias}"
    assert rows[0]["data"].get("reason") == reason, f"activity: {rows[0]}"


@then('the company "{alias}" is not marked do not contact')
def step_not_dnc(context, alias):
    company = ok(context.api.get(url(context, LEADS, f"companies/{context.saved[alias]}/")))
    assert company["do_not_contact"] is False, f"company: {company}"


@then('the people search of the company "{alias}" is done with the mail pattern "{pattern}"')
def step_search_done(context, alias, pattern):
    search = finished_search(context, alias)
    assert (search["status"], search["mail_pattern"]) == ("done", pattern), f"search: {search}"
    assert search["reason"] in {"wrong_person", "opted_out"} and search["requested_by"] == "leads", f"search: {search}"
    assert search["pattern_source"], f"the pattern has no source: {search}"


@then('the company "{alias}" has {count:d} candidates waiting for review')
def step_waiting(context, alias, count):
    waiting = [row for row in candidates(context, alias) if row["status"] == "pending"]
    assert len(waiting) == count, f"waiting: {waiting}"


# --- Checks ---


@then('the candidate "{last_name}" of the company "{alias}" has every check "ok"')
def step_all_ok(context, last_name, alias):
    row = candidate(context, alias, last_name)
    assert {kind: check["result"] for kind, check in checks(row).items()} == dict.fromkeys(
        ("role", "email", "employed", "mailbox"), "ok"
    ), f"candidate: {row}"
    assert row["missing"] == [], f"candidate: {row}"


@then('the candidate "{last_name}" of the company "{alias}" has the address "{local}" at the company\'s domain')
def step_address(context, last_name, alias, local):
    row = candidate(context, alias, last_name)
    assert row["email"] == f"{local}{context.saved[f'{alias}.domain']}", f"candidate: {row}"


@then('the candidate "{last_name}" of the company "{alias}" has the check "{kind}" "{result}" after {tries:d} tries')
def step_check(context, last_name, alias, kind, result, tries):
    row = candidate(context, alias, last_name)
    check = checks(row)[kind]
    assert (check["result"], check["attempts"]) == (result, tries), f"check: {check}"
    assert kind in row["missing"], f"candidate: {row}"


@then('every check "ok" of the candidates of the company "{alias}" has a source and a date')
def step_sources(context, alias):
    for row in candidates(context, alias):
        assert row["source"] and row["found_at"], f"candidate: {row}"
        for check in row["checks"]:
            if check["result"] == "ok":
                assert check["source"] and check["checked_at"], f"{row['last_name']}: {check}"


# --- Decisions ---


@when('the candidate "{last_name}" of the company "{alias}" is accepted')
def step_accept(context, last_name, alias):
    row = candidate(context, alias, last_name)
    ok(context.api.post(url(context, PROSPECTING, f"people/candidates/{row['id']}/accept/"), json={}))


@when('the candidate "{last_name}" of the company "{alias}" is rejected')
def step_reject(context, last_name, alias):
    row = candidate(context, alias, last_name)
    ok(context.api.post(url(context, PROSPECTING, f"people/candidates/{row['id']}/reject/"), json={"reason": "bdd"}))


@then('the candidate "{last_name}" of the company "{alias}" is "{status}"')
def step_status(context, last_name, alias, status):
    row = candidate(context, alias, last_name)
    assert row["status"] == status, f"candidate: {row}"


@then('accepting the candidate "{last_name}" of the company "{alias}" again is refused')
def step_accept_again(context, last_name, alias):
    row = candidate(context, alias, last_name)
    response = context.api.post(url(context, PROSPECTING, f"people/candidates/{row['id']}/accept/"), json={})
    assert response.status_code == 409, f"{response.status_code}: {response.text[:300]}"


@then('the company "{alias}" has a contact "{local}" with the source "{source}" and no mail block')
def step_new_contact(context, alias, local, source):
    address = f"{local}{context.saved[f'{alias}.domain']}"
    row = next((row for row in contacts(context, alias) if row["email"] == address), None)
    assert row is not None, f"no contact {address}: {contacts(context, alias)}"
    assert row["source"] == source and not row["mail_block"], f"contact: {row}"


@then('the company "{alias}" has no contact with the local part "{local}"')
def step_no_contact(context, alias, local):
    address = f"{local}{context.saved[f'{alias}.domain']}"
    assert all(row["email"] != address for row in contacts(context, alias)), contacts(context, alias)


# --- The referral request (communicator) ---


def referral(context, alias: str) -> dict | None:
    """The newest review draft of the alias's address that is a referral request. The queue lists the oldest first
    and a long run leaves more than one page in it, so the pages are read from the last one back."""
    email = context.saved[f"{alias}.email"]
    size = 100
    params = {"status": "review_required", "page_size": size}
    first = ok(context.api.get(url(context, COMMUNICATOR, "review/"), params=params))
    pages = max(1, -(-first["count"] // size))
    for page in range(pages, 0, -1):
        rows = (
            first["results"]
            if page == 1
            else ok(context.api.get(url(context, COMMUNICATOR, "review/"), params={**params, "page": page}))["results"]
        )
        for row in reversed(rows):
            if row.get("referral_request") is False:
                continue
            detail = ok(context.api.get(url(context, COMMUNICATOR, f"review/{row['id']}/")))
            if detail.get("referral_request") and detail["thread"]["recipient_email"] == email:
                return detail
    return None


@then('the review queue has a referral request to the contact of "{alias}"')
def step_referral(context, alias):
    draft = poll(lambda: referral(context, alias))
    assert draft, f"no referral request to {context.saved[f'{alias}.email']}"
    assert draft["status"] == "review_required" and draft["subject"].lower().startswith("re:"), f"draft: {draft}"
    context.saved[f"{alias}.referral"] = draft["id"]


@then('approving the referral request of "{alias}" succeeds')
def step_approve_referral(context, alias):
    path = f"review/{context.saved[f'{alias}.referral']}/accept/"
    message = ok(context.api.post(url(context, COMMUNICATOR, path), json={}))
    assert message["status"] == "approved", f"message: {message}"
