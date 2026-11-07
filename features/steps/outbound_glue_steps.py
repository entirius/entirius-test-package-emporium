# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps of the outbound glue scenarios (leads <-> communicator). They address the communicator through the same
dev endpoint as the Q3 steps, with a `subject_ref` that names the leads company, so leads' receivers find it. Reuses
the Q3 step texts for routes, the send task, status and failure code, and the Q5 steps for the company and its
contact."""

from __future__ import annotations

import email
import re

from behave import then, when

from entirius_tests import mail

LEADS = "api/leads/v2/admin/{channel}/"
COMMUNICATOR = "api/communicator/v2/admin/{channel}/"
UNSUBSCRIBE_RE = re.compile(r"<(https?://[^>]+/api/communicator/v2/public/unsubscribe/[^>]+)>")
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."


def _ok(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


def _contact(context, alias: str, *, first: bool) -> dict:
    """The contact added by the Q5 address step, else the first contact of the company."""
    if not first and f"{alias}.contact" in context.saved:
        return _ok(
            context.api.get(
                context.api.url(
                    LEADS.format(channel=context.channel) + f"contacts/{context.saved[f'{alias}.contact']}/"
                )
            )
        )
    rows = _ok(
        context.api.get(
            context.api.url(LEADS.format(channel=context.channel) + f"contacts/?company={context.saved[alias]}")
        )
    )
    return rows["results"][0]


def _create(context, alias: str, route: str, msg: str, *, first: bool) -> None:
    contact = _contact(context, alias, first=first)
    body = {
        "template_key": "followup",
        "recipient": {"email": contact["email"], "first_name": "Jan", "language": "pl", "legal_footer": LEGAL_FOOTER},
        "context": {"company_name": "Example Shop 1", "body": "BDD wiadomość testowa."},
        "subject_ref": f"leads.Company:{context.saved[alias]}",
        "requires_review": False,
        "sender_route": route,
    }
    url = context.api.url(COMMUNICATOR.format(channel=context.channel) + "test/communicate/")
    data = _ok(context.api.post(url, json=body), 201)
    context.saved[msg] = data["id"]


@when(
    'I create a routed approved message to the contact of the company "{alias}" on the sender route "{route}" as "{msg}"'
)
def step_create_contact(context, alias, route, msg):
    _create(context, alias, route, msg, first=False)


@when(
    'I create a routed approved message to the first contact of the company "{alias}" on the sender route "{route}" as "{msg}"'
)
def step_create_first(context, alias, route, msg):
    _create(context, alias, route, msg, first=True)


def _sandbox_mails(recipient: str) -> list[email.message.Message]:
    parsed = [email.message_from_string(m["mimeMessage"]) for m in mail.list_messages()]
    return [m for m in parsed if m["X-Original-To"] == recipient]


@then('the sandbox mailbox holds no message to the contact of the company "{alias}"')
def step_no_mail(context, alias):
    address = _contact(context, alias, first=False)["email"]
    assert not _sandbox_mails(address), f"unexpected sandbox mail to {address}"


@when(
    'the unsubscribe link of the sandbox message to the first contact of the company "{alias}" is posted as a one-click request'
)
def step_post_link(context, alias):
    address = _contact(context, alias, first=True)["email"]
    found = _sandbox_mails(address)
    assert found, f"no sandbox message to {address}"
    header = found[-1]["List-Unsubscribe"]
    if not header:
        context.scenario.skip("COMMUNICATOR_UNSUBSCRIBE_BASE_URL is not set in the stack")
        return
    link = UNSUBSCRIBE_RE.match(header.strip())
    assert link, f"List-Unsubscribe {header!r}"
    context.response = context.api.post(
        link.group(1), data="List-Unsubscribe=One-Click", headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
