# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads steps — only what the shared v2 admin steps lack: a multipart CSV upload, polling an import batch,
a contact_forms submission with the channel's API key, field checks on list items, and the pipeline checks of
plan 10 (timeline, rule runs, review queue, sequence walk) that poll worker-side effects."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from datetime import time as dt_time
from pathlib import Path

import requests
from behave import given, then, when

from entirius_tests import clock, mail

# X-API-KEY values of fixtures/django_contact_forms.cfg.yaml (apikey pk 1 and 2).
CONTACT_FORM_API_KEYS = {"default-europe": "1" * 64, "default-local": "2" * 64}
IMPORT_TIMEOUT_S = 60


def _v2_url(context, path: str) -> str:
    """`leads/admin/{channel_idx}/x/` → `<base>/api/leads/v2/admin/<channel>/x/`, saved aliases resolved."""
    resolved = path.replace("{channel_idx}", context.channel or "")
    for key, value in (context.saved or {}).items():
        resolved = resolved.replace(f"{{{key}}}", str(value))
    module, _, rest = resolved.partition("/")
    return context.api.url(f"api/{module}/v2/{rest}")


def _results(context) -> list[dict]:
    data = context.response_data
    return data.get("results", []) if isinstance(data, dict) else data


@when('I upload the package file "{name}" to the v2 admin endpoint "{path}"')
def step_upload_package_file(context, name, path):
    url = _v2_url(context, path)
    file_path = Path(context.test_package_path) / name
    with file_path.open("rb") as handle:
        context.response = context.api.post(url, files={"file": (name, handle, "text/csv")})
    context.response_data = context.response.json()


@then('the import batch "{alias}" has finished')
def step_import_batch_finished(context, alias):
    url = _v2_url(context, f"leads/admin/{{channel_idx}}/imports/{context.saved[alias]}/")
    deadline = time.monotonic() + IMPORT_TIMEOUT_S
    while True:
        context.response = context.api.get(url)
        context.response_data = context.response.json()
        if context.response_data.get("status") in ("done", "failed") or time.monotonic() > deadline:
            break
        time.sleep(1)
    assert context.response_data.get("status") == "done", f"import batch: {context.response_data}"


@when('I submit a contact form on channel "{idx}" with body')
def step_submit_contact_form(context, idx):
    url = context.api.url(f"api/contact-forms/v2/{idx}/submit/")
    headers = {"X-API-KEY": CONTACT_FORM_API_KEYS[idx]}
    context.response = requests.post(url, json=json.loads(context.text), headers=headers, timeout=30)
    assert context.response.status_code == 201, f"submit: {context.response.status_code} {context.response.text[:300]}"


@then("the import counts created plus matched should equal {total:d}")
def step_import_imported_total(context, total):
    data = context.response_data
    assert data["created_count"] + data["matched_count"] == total, f"import counts: {data}"


@then('the import report should contain the reason "{reason}"')
def step_report_reason(context, reason):
    reasons = {entry["reason"] for entry in context.response_data["report"]}
    assert reason in reasons, f"reasons: {sorted(reasons)}"


@then('the result with "{key}" equal to "{value}" should have a null "{field}"')
def step_result_field_null(context, key, value, field):
    items = [item for item in _results(context) if str(item.get(key)) == value]
    assert items, f"no result with {key}={value}"
    assert items[0][field] is None, f"{field}: {items[0][field]!r}"


# --- Pipeline (plan 10): rules, intel, rotation. Worker-side effects are polled. ---

POLL_TIMEOUT_S = 90
COMMUNICATOR_ADMIN = "api/communicator/v2/admin/{channel}/"
SEQUENCE_MAX_DAYS = 40


def _poll(check, timeout: float = POLL_TIMEOUT_S):
    """`check()` until it returns a truthy value; the last value (falsy on timeout) is returned."""
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value or time.monotonic() > deadline:
            return value
        time.sleep(1)


def _get_json(context, url: str) -> dict:
    response = context.api.get(url)
    assert response.status_code == 200, f"GET {url}: {response.status_code} {response.text[:300]}"
    return response.json()


def _comm_url(context, path: str) -> str:
    return context.api.url(COMMUNICATOR_ADMIN.format(channel=context.channel) + path)


def _company_url(context, alias: str, path: str = "") -> str:
    return _v2_url(context, f"leads/admin/{{channel_idx}}/{path}".replace("{company}", str(context.saved[alias])))


@given('the leads company "{domain}" exists as "{alias}"')
def step_company_exists(context, domain, alias):
    context.api.post(_v2_url(context, "leads/admin/{channel_idx}/companies/"), json={"domain": domain})
    results = _get_json(context, _v2_url(context, f"leads/admin/{{channel_idx}}/companies/?search={domain}"))["results"]
    assert results, f"company {domain} was not created"
    context.saved[alias] = results[0]["id"]


@when('I run the leads test action "{name}" with body')
def step_leads_test_action(context, name):
    body = context.text
    for key, value in (context.saved or {}).items():
        body = body.replace(f"{{{key}}}", str(value))
    url = _v2_url(context, f"leads/admin/{{channel_idx}}/test/{name}/")
    context.response = context.api.post(url, json=json.loads(body))
    context.response_data = context.response.json()
    assert context.response.status_code == 200, (
        f"test/{name}: {context.response.status_code} {context.response.text[:300]}"
    )


@when('the company "{alias}" moves through the stages "{keys}"')
def step_company_moves(context, alias, keys):
    url = _company_url(context, alias, "companies/{company}/transition/")
    for key in (part.strip() for part in keys.split(",")):
        response = context.api.post(url, json={"stage_key": key})
        assert response.status_code == 200, f"transition {key}: {response.status_code} {response.text[:300]}"


@then('the company "{alias}" has an activity "{kind}" containing "{text}"')
def step_company_activity(context, alias, kind, text):
    url = _company_url(context, alias, "activities/?company={company}&page_size=100")

    def found():
        rows = _get_json(context, url)["results"]
        return [row for row in rows if row["kind"] == kind and text in row["message"]]

    assert _poll(found), f"no {kind} activity containing {text!r} for company {context.saved[alias]}"


@then('the company "{alias}" has a rule run "{outcome}"')
def step_company_rule_run(context, alias, outcome):
    url = _company_url(context, alias, "rule-runs/?company={company}&page_size=100")
    assert _poll(lambda: any(run["outcome"] == outcome for run in _get_json(context, url)["results"])), (
        f"no {outcome} rule run for company {context.saved[alias]}"
    )


@then('the company "{alias}" is in stage "{key}"')
def step_company_stage(context, alias, key):
    url = _company_url(context, alias, "companies/{company}/")
    assert _poll(lambda: _get_json(context, url)["stage"]["key"] == key), f"company is not in stage {key}"


@then('the company "{alias}" has rotation count {count:d}')
def step_company_rotation_count(context, alias, count):
    url = _company_url(context, alias, "companies/{company}/")
    data = _poll(lambda: (lambda row: row if row["rotation_count"] == count else None)(_get_json(context, url)))
    assert data, f"rotation_count of company {context.saved[alias]} never reached {count}"


def _review_items(context, alias: str) -> list[dict]:
    ref = f"leads.Company:{context.saved[alias]}"
    rows = _get_json(context, _comm_url(context, "review/?page_size=100"))["results"]
    return [row for row in rows if row.get("thread", {}).get("subject_ref") == ref]


@then('the review queue holds a draft about the company "{alias}"')
def step_review_holds(context, alias):
    assert _poll(lambda: _review_items(context, alias)), f"no review draft for company {context.saved[alias]}"


@then('the review queue holds no draft about the company "{alias}"')
def step_review_empty(context, alias):
    assert not _review_items(context, alias), f"review drafts for company {context.saved[alias]}"


@when('the follow-up sequence to "{email}" about the company "{alias}" has finished')
def step_sequence_finished(context, email, alias):
    thread = _poll(lambda: _thread(context, alias, email))
    assert thread, f"no thread to {email} about company {context.saved[alias]}"
    _finish_sequence(context, alias, thread)


@when('the latest follow-up sequence about the company "{alias}" has finished')
def step_latest_sequence_finished(context, alias):
    threads = _threads(context, alias)
    assert threads, f"no thread about company {context.saved[alias]}"
    _finish_sequence(context, alias, max(threads, key=lambda row: row["id"]))


def _finish_sequence(context, alias: str, thread: dict) -> None:
    """Accept the thread's draft on the reference Monday, send it, start `followup`, then move the channel clock a
    day at a time with a beat run each day until the sequence stops `finished`."""
    start = datetime.combine(clock.reference_day("monday"), dt_time(10, 0))
    days = [start.date() + timedelta(days=offset) for offset in range(SEQUENCE_MAX_DAYS)]
    clock.reset_send_counters(context.api, context.channel, days)
    context.add_cleanup(clock.clear_channel_clock, context.api, context.channel)
    clock.set_channel_clock(context.api, context.channel, start.isoformat())
    for item in (
        _poll(lambda: [row for row in _review_items(context, alias) if row["thread"]["id"] == thread["id"]]) or []
    ):
        response = context.api.post(_comm_url(context, f"review/{item['id']}/accept/"), json={})
        assert response.status_code == 200, f"accept {item['id']}: {response.status_code} {response.text[:300]}"
    clock.run_beat_send(context.api, context.channel)
    response = context.api.post(
        _comm_url(context, "test/start-sequence/"), json={"thread_id": thread["id"], "sequence_key": "followup"}
    )
    assert response.status_code == 201, f"start-sequence: {response.status_code} {response.text[:300]}"
    for day in days[1:]:
        clock.set_channel_clock(context.api, context.channel, datetime.combine(day, dt_time(10, 0)).isoformat())
        clock.run_beat_send(context.api, context.channel)
        state = _get_json(context, _comm_url(context, f"threads/{thread['id']}/")).get("sequence") or {}
        if state.get("stop_reason"):
            assert state["stop_reason"] == "finished", f"sequence stopped: {state}"
            return
    raise AssertionError(f"sequence of thread {thread['id']} not finished after {SEQUENCE_MAX_DAYS} days")


def _threads(context, alias: str) -> list[dict]:
    ref = f"leads.Company:{context.saved[alias]}"
    return _get_json(context, _comm_url(context, f"threads/?subject_ref={ref}&page_size=100"))["results"]


def _thread(context, alias: str, email: str) -> dict | None:
    return next((row for row in _threads(context, alias) if row["recipient_email"] == email), None)


# --- Retention and GDPR (plan 11) ---


def _resolve(context, text: str) -> str:
    for key, value in (context.saved or {}).items():
        text = text.replace(f"{{{key}}}", str(value))
    return text


def _relative_iso(value: str) -> str:
    """`+N day(s)` → ISO timestamp N days from now (UTC); anything else is passed through as ISO."""
    if not value.startswith("+"):
        return value
    days = int(value[1:].split()[0])
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


@given('the leads contact "{email}" of the company "{domain}" is saved as "{alias}"')
def step_contact_saved(context, email, domain, alias):
    """Saves the contact id as `alias`, its company id as `alias.company` and its email as `alias.email`."""
    companies = _get_json(context, _v2_url(context, f"leads/admin/{{channel_idx}}/companies/?search={domain}"))
    assert companies["results"], f"company {domain} not seeded"
    company_id = companies["results"][0]["id"]
    detail = _get_json(context, _v2_url(context, f"leads/admin/{{channel_idx}}/companies/{company_id}/"))
    contact = next((row for row in detail["contacts"] if row["email"] == email), None)
    assert contact, f"contact {email} not in company {domain}"
    context.saved.update({alias: contact["id"], f"{alias}.company": company_id, f"{alias}.email": email})


@given('the communicator thread to "{email}" about the company "{alias}" is saved as "{thread_alias}"')
def step_thread_saved(context, email, alias, thread_alias):
    thread = _thread(context, alias, email)
    assert thread, f"no thread to {email} about company {context.saved[alias]}"
    context.saved[thread_alias] = thread["id"]


@when('I run the leads test action "anonymise-now" as of "{when}"')
def step_anonymise_now(context, when):
    url = _v2_url(context, "leads/admin/{channel_idx}/test/anonymise-now/")
    context.response = context.api.post(url, json={"as_of": _relative_iso(when)})
    context.response_data = context.response.json()
    assert context.response.status_code == 200, f"anonymise-now: {context.response.status_code} {context.response.text}"


def _contact(context, alias: str) -> dict:
    return _get_json(context, _v2_url(context, f"leads/admin/{{channel_idx}}/contacts/{context.saved[alias]}/"))


@then('the contact "{alias}" is anonymised')
def step_contact_anonymised(context, alias):
    """Also replaces `alias.email` with the stored token for later steps."""
    contact = _contact(context, alias)
    assert contact["email"].startswith("anon-") and contact["anonymised_at"], f"contact not anonymised: {contact}"
    assert (contact["first_name"], contact["last_name"], contact["phone"]) == ("", "", ""), contact
    context.saved[f"{alias}.email"] = contact["email"]


@then('the contact "{alias}" is not anonymised')
def step_contact_not_anonymised(context, alias):
    contact = _contact(context, alias)
    assert contact["email"] == context.saved[f"{alias}.email"] and contact["anonymised_at"] is None, contact


@then('the communicator thread "{alias}" has recipient "{email}"')
def step_thread_recipient(context, alias, email):
    thread = _get_json(context, _comm_url(context, f"threads/{context.saved[alias]}/"))
    expected = _resolve(context, email)
    assert (thread["recipient_email"], thread["recipient_name"]) == (expected, ""), thread


@then('the GDPR response lists the modules "{names}"')
def step_gdpr_modules(context, names):
    modules = context.response_data["modules"]
    missing = [name.strip() for name in names.split(",") if name.strip() not in modules]
    assert not missing, f"modules missing from the export: {missing} (got {sorted(modules)})"


@then('the GDPR erasure touched rows in "{names}"')
def step_gdpr_erased(context, names):
    modules = context.response_data["modules"]
    for name in (part.strip() for part in names.split(",")):
        assert sum(modules.get(name, {}).values()) > 0, f"{name} erased nothing: {modules}"


@then('the communicator suppressions list the global token "{token}"')
def step_suppression_token_listed(context, token):
    """Filtered by value on the server (the list is not paged by the client): the erased address's token row."""
    token = _resolve(context, token)
    rows = _get_json(context, _comm_url(context, f"suppressions/?value={token}"))["results"]
    assert [row for row in rows if row["kind"] == "email_token" and row["value"] == token], f"{token} not suppressed"


@then('the GDPR export lists "{email}" in "{sections}"')
def step_gdpr_export_lists(context, email, sections):
    """Each `module.Model` section holds rows, and every row belongs to the subject (its email or recipient)."""
    email, modules = _resolve(context, email), context.response_data["modules"]
    for section in (part.strip() for part in sections.split(",")):
        module, _, model = section.partition(".")
        rows = modules.get(module, {}).get(model, [])
        owners = {row.get("email") or row.get("recipient_email") for row in rows}
        assert rows and owners == {email}, f"{section}: expected rows of {email}, got {owners or 'none'}"


@then('the GDPR export holds no "{email}"')
def step_gdpr_export_holds_no(context, email):
    exported = json.dumps(context.response_data["modules"])
    assert email not in exported, "the plain address is still stored after the erasure"


@when('I import the leads contact "{email}" of the company "{domain}"')
def step_import_contact(context, email, domain):
    header = "company_name,domain,website,company_type,industry,first_name,last_name,email,job_title,language,legal_basis,phone"
    content = f"{header}\nReimport,{domain},,,,Re,Import,{email},,,consent,\n"
    url = _v2_url(context, "leads/admin/{channel_idx}/test/import-now/")
    context.response = context.api.post(url, files={"file": ("reimport.csv", content.encode(), "text/csv")})
    context.response_data = context.response.json()
    assert context.response.status_code == 200, f"import-now: {context.response.status_code} {context.response.text}"


@then('the company "{alias}" has no contact "{email}"')
def step_company_has_no_contact(context, alias, email):
    detail = _get_json(context, _v2_url(context, f"leads/admin/{{channel_idx}}/companies/{context.saved[alias]}/"))
    emails = [row["email"] for row in detail["contacts"]]
    assert email not in emails and len(emails) == 1, f"contacts of the company: {len(emails)}"


@given("the sandbox mailbox count is remembered")
def step_mailbox_remember(context):
    context.saved["mailbox_count"] = mail.count()


@when("the communicator beat sends due messages")
def step_beat_send(context):
    response = clock.run_beat_send(context.api, context.channel)
    assert response.status_code == 200, f"send-due: {response.status_code} {response.text[:300]}"


@then("the sandbox mailbox count is unchanged")
def step_mailbox_unchanged(context):
    time.sleep(2)
    assert mail.count() == context.saved["mailbox_count"], "a message reached the sandbox mailbox"
