# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps of the outbound Q3 (sender route), Q5 (address verification) and Q7 (do not contact, send check) scenarios.
Every scenario imports its own company; nothing consumes the seed. No DNS is needed: the invalid address is a
disposable domain, which the check rejects before any lookup."""

from __future__ import annotations

import io
import time

from behave import given, then, when

LEADS = "api/leads/v2/admin/{channel}/"
HEADER = (
    "company_name,domain,website,lead_type,industry,first_name,last_name,email,job_title,language,legal_basis,phone"
)
TIMEOUT_S = 60


def _url(context, path: str) -> str:
    return context.api.url(LEADS.format(channel=context.channel) + path)


def _json(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


def _poll(check):
    deadline = time.monotonic() + TIMEOUT_S
    while True:
        value = check()
        if value or time.monotonic() > deadline:
            return value
        time.sleep(1)


def _contact(context, alias: str) -> dict:
    rows = _json(context.api.get(_url(context, f"contacts/?company={context.saved[alias]}")))["results"]
    assert rows, f"company {alias} has no contact"
    return rows[0]


@given('a fresh company is imported through the sender route "{route}" as "{alias}"')
def step_import_with_route(context, route, alias):
    token = time.time_ns()
    domain, address = f"bdd-q3-{token}.test", f"owner@bdd-q3-{token}.test"
    row = f"BDD {token},{domain},,RETAILER,garden,Ewa,Nowak,{address},Owner,pl,legitimate_interest,"
    content = io.BytesIO(f"{HEADER}\n{row}\n".encode())
    batch = _json(
        context.api.post(
            _url(context, "imports/"), files={"file": ("bdd-q3.csv", content, "text/csv")}, data={"sender_route": route}
        ),
        202,
    )
    assert batch["sender_route"] == route
    done = _poll(lambda: _json(context.api.get(_url(context, f"imports/{batch['id']}/"))).get("status") == "done")
    assert done, f"import batch {batch['id']} did not finish"
    found = _json(context.api.get(_url(context, f"companies/?search={domain}")))["results"]
    assert len(found) == 1, f"expected one company {domain}"
    context.saved[alias] = found[0]["id"]


@when('the sender route of the company "{alias}" is changed to "{route}" in bulk')
def step_bulk_route(context, alias, route):
    body = {"company_ids": [context.saved[alias]], "sender_route": route}
    assert _json(context.api.post(_url(context, "companies/bulk-sender-route/"), json=body)) == {"updated": 1}


@then('the company "{alias}" has the sender route "{route}"')
def step_company_route(context, alias, route):
    company = _json(context.api.get(_url(context, f"companies/{context.saved[alias]}/")))
    assert company["sender_route"] == route, f"route: {company['sender_route']!r}"


@given('the contact of the company "{alias}" gets the address "{email}"')
@when('the contact of the company "{alias}" gets the address "{email}"')
def step_replace_contact(context, alias, email):
    """The imported contact keeps its address (immutable), so a second contact with the given address is added."""
    token = time.time_ns()
    local, _, host = email.partition("@")
    body = {
        "company_id": context.saved[alias],
        "email": f"{local}-{token}@{host}",
        "legal_basis": "legitimate_interest",
        "is_primary": True,
    }
    created = _json(context.api.post(_url(context, "contacts/"), json=body), 201)
    context.saved[f"{alias}.contact"] = created["id"]


@when('the address of the contact of the company "{alias}" is verified')
def step_verify(context, alias):
    context.response_data = _json(context.api.post(_url(context, f"contacts/{context.saved[f'{alias}.contact']}/verify/")))


@then('the verification status is "{status}" with the reason "{reason}"')
def step_status(context, status, reason):
    data = context.response_data
    assert (data["email_status"], data["email_status_reason"]) == (status, reason), data


@then('the invalid addresses list contains the contact of the company "{alias}"')
def step_invalid_list(context, alias):
    rows = _json(context.api.get(_url(context, "contacts/?email_status=invalid&page_size=100")))["results"]
    assert context.saved[f"{alias}.contact"] in {row["id"] for row in rows}


@then('the send check of the contact of the company "{alias}" refuses with "{reason}"')
def step_refuses(context, alias, reason):
    check = _json(context.api.get(_url(context, f"contacts/{context.saved[f'{alias}.contact']}/send-check/")))
    assert check["eligible"] is False and reason in check["reasons"], check


@then('the send check of the first contact of the company "{alias}" allows outreach and names the legal basis')
def step_allows(context, alias):
    contact = _contact(context, alias)
    check = _json(context.api.get(_url(context, f"contacts/{contact['id']}/send-check/")))
    assert check["eligible"] is True and check["reasons"] == [], check
    assert check["legal_basis"]["value"] == "legitimate_interest" and check["retention"]["days"] > 0, check


@when('the email of the first contact of the company "{alias}" is put on the do-not-contact list')
def step_dnc(context, alias):
    email = _contact(context, alias)["email"]
    body = {"email": email, "reason": "bdd opt-out request"}
    assert _json(context.api.post(_url(context, "do-not-contact/"), json=body), 201)["contacts"] >= 1


@then('the send check of the first contact of the company "{alias}" refuses with "{reason}"')
def step_first_refuses(context, alias, reason):
    contact = _contact(context, alias)
    check = _json(context.api.get(_url(context, f"contacts/{contact['id']}/send-check/")))
    assert check["eligible"] is False and reason in check["reasons"], check


@then('drafting a mail to the company "{alias}" is refused by the outreach gate')
def step_gate_refuses(context, alias):
    contact = _contact(context, alias)
    response = context.api.post(
        _url(context, f"companies/{context.saved[alias]}/communicate/"),
        json={"template_key": "bdd-any", "contact_id": contact["id"]},
    )
    assert response.status_code == 409, f"{response.status_code}: {response.text[:200]}"
