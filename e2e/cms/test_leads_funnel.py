# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads funnel in the CMS (mode B of guides/leads-end-to-end-testing): steps 3-7 clicked on phone and desktop.

`make e2e-funnel` runs this file twice on the same seed (E2E_DEVICE="iPhone 14", then desktop), so every test
builds its own state by API: a fresh thread per run (unique recipient on a seeded company) and an Inbox holding
only its own draft (every other `review_required` draft is skipped first). Steps 1-2 (import, audit) are
consumed by `@funnel` on a seed — the draft of step 3 comes from the communicator test endpoint instead, with
the company's hooks as its render context. The reply mail is dated a minute after the channel clock sent it.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from email.utils import format_datetime
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from entirius_tests import clock, mail
from entirius_tests.api_client import ApiClient
from entirius_tests.auth import obtain_jwt_token
from entirius_tests.cms_e2e import ADMIN_PASSWORD, ADMIN_USERNAME, API_BASE_URL, require_module
from entirius_tests.cms_pages import InboxPage, NotificationBar, ThreadPage

pytestmark = require_module("leads")

CHANNEL = "default-europe"
COMMUNICATOR = f"api/communicator/v2/admin/{CHANNEL}/"
LEADS = f"api/leads/v2/admin/{CHANNEL}/"
MAIL_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "mail"
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."
MAX_TAPS_TO_ACCEPT = 3
MESSAGE_ID_HEADER = re.compile(rb"^Message-ID: .*$", re.MULTILINE)
DATE_HEADER = re.compile(rb"^Date: .*$", re.MULTILINE)


@pytest.fixture
def api() -> ApiClient:
    client = ApiClient(base_url=API_BASE_URL)
    client.set_auth_token(obtain_jwt_token(API_BASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD))
    return client


def _ok(response, status: int = 200) -> dict:
    assert response.status_code == status, (
        f"{response.request.method} {response.url}: {response.status_code} {response.text}"
    )
    return response.json()


def _company(api: ApiClient, domain: str) -> dict:
    found = _ok(api.get(api.url(f"{LEADS}companies/?search={domain}")))["results"]
    assert found, f"seeded company {domain} missing — run make seed"
    return _ok(api.get(api.url(f"{LEADS}companies/{found[0]['id']}/")))


def _clear_review_queue(api: ApiClient) -> None:
    for draft in _ok(api.get(api.url(f"{COMMUNICATOR}review/?status=review_required&page_size=100")))["results"]:
        api.post(api.url(f"{COMMUNICATOR}review/{draft['id']}/skip/"), json={"reason": "e2e reset"})


def _communicate(api: ApiClient, company: dict, *, requires_review: bool) -> dict:
    tag = time.time_ns()
    body = {
        "template_key": "followup",
        "recipient": {
            "email": f"e2e-{tag}@{company['domain']}",
            "first_name": "Anna",
            "language": "pl",
            "legal_footer": LEGAL_FOOTER,
        },
        "context": {
            "company_name": f"E2E {tag}",
            "body": "E2E funnel draft.",
            "hooks": company["hooks"],
            "platform": company["platform"],
        },
        "subject_ref": f"leads.Company:{company['id']}",
        "requires_review": requires_review,
    }
    return _ok(api.post(api.url(f"{COMMUNICATOR}test/communicate/"), json=body), 201)


def _send(api: ApiClient, message: dict) -> dict:
    """Moves the channel clock to the message's slot (else the policy's next slot), clears that day's send counter
    (the phone and desktop runs share the daily cap) and runs the beat; returns the sent message."""
    slot = message.get("scheduled_at") or _ok(api.get(api.url(f"{COMMUNICATOR}policy/")))["next_slot"]
    _ok(clock.reset_send_counters(api, CHANNEL, [datetime.fromisoformat(slot).date()]))
    _ok(clock.set_channel_clock(api, CHANNEL, slot))
    _ok(clock.run_beat_send(api, CHANNEL))
    sent = _ok(api.get(api.url(f"{COMMUNICATOR}messages/?status=sent&page_size=100")))["results"]
    found = [m for m in sent if m["id"] == message["id"]]
    assert found, f"message {message['id']} was not sent"
    return found[0]


def _reply(api: ApiClient, sent: dict, fixture: str) -> None:
    eml = mail.render_fixture(MAIL_FIXTURES / fixture, sent["message_id"])
    written = format_datetime(datetime.fromisoformat(sent["sent_at"]) + timedelta(minutes=1))
    eml = DATE_HEADER.sub(lambda _: f"Date: {written}".encode(), eml, count=1)
    eml = MESSAGE_ID_HEADER.sub(lambda _: f"Message-ID: <e2e-{time.time_ns()}@inbound.test>".encode(), eml, count=1)
    mail.append_raw(eml)
    _ok(clock.run_imap_poll(api, CHANNEL))


def _accept_in_inbox(page: Page, draft: dict) -> InboxPage:
    inbox = InboxPage(page)
    inbox.open()
    inbox.open_draft(draft["subject"])
    inbox.send()
    inbox.expect_scheduled()
    return inbox


def test_C07_accept_from_inbox_schedules(admin_page: Page, api: ApiClient):
    _clear_review_queue(api)
    draft = _communicate(api, _company(api, "example-shop-4.test"), requires_review=True)
    inbox = _accept_in_inbox(admin_page, draft)
    assert inbox.has_no_horizontal_scroll()
    approved = _ok(api.get(api.url(f"{COMMUNICATOR}review/?status=approved&page_size=100")))["results"]
    accepted = [m for m in approved if m["id"] == draft["id"]]
    assert accepted and accepted[0]["scheduled_at"] and accepted[0]["reviewed_by_id"]
    inbox.expect_empty_with_scheduled()


def test_funnel_steps_3_to_7(admin_page: Page, api: ApiClient):
    _clear_review_queue(api)
    company = _company(api, "example-shop-5.test")
    draft = _communicate(api, company, requires_review=True)  # step 3
    inbox = _accept_in_inbox(admin_page, draft)  # step 4
    assert inbox.taps <= MAX_TAPS_TO_ACCEPT, f"accepting a draft took {inbox.taps} taps"
    approved = _ok(api.get(api.url(f"{COMMUNICATOR}review/?status=approved&page_size=100")))["results"]
    sent = _send(api, next(m for m in approved if m["id"] == draft["id"]))  # step 5
    thread = ThreadPage(admin_page)
    thread.open(company["id"])
    thread.expect_outbound(draft["subject"], "sent")
    assert admin_page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    _reply(api, sent, "reply_plain.eml")  # step 6
    admin_page.reload()
    thread.expect_reply("can we talk on Thursday")
    bar = NotificationBar(admin_page)  # step 7
    bar.expect_unread()
    bar.open()
    bar.open_row(f"Reply from {company['name']}")
    thread.expect_reply("can we talk on Thursday")


def test_C23_optout_confirm_from_thread(admin_page: Page, api: ApiClient):
    company = _company(api, "example-shop-6.test")
    message = _communicate(api, company, requires_review=False)
    _reply(api, _send(api, message), "optout_pl.eml")
    thread = ThreadPage(admin_page)
    thread.open(company["id"])
    thread.confirm_optout()
    replies = _ok(api.get(api.url(f"{COMMUNICATOR}replies/?thread={message['thread']['id']}")))["results"]
    assert replies[0]["kind"] == "suspected_optout" and replies[0]["optout_confirmed_at"]


def test_N01_high_notification_in_bar(admin_page: Page, api: ApiClient):
    company = _company(api, "example-shop-4.test")
    _reply(api, _send(api, _communicate(api, company, requires_review=False)), "reply_plain.eml")
    admin_page.goto(admin_page.url)
    bar = NotificationBar(admin_page)
    bar.expect_unread()
    bar.open()
    expect(
        admin_page.get_by_test_id("notif-row").filter(has_text=f"Reply from {company['name']}").first
    ).to_be_visible()
    bar.open_row(f"Reply from {company['name']}")
    expect(admin_page.get_by_test_id("thread-company")).to_have_text(company["name"])
