# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads funnel in the CMS (mode B of guides/leads-end-to-end-testing): steps 1-7 clicked on desktop, 3-7 on a phone.

`make e2e-funnel` runs this file twice on the same seed (E2E_DEVICE="iPhone 14", then desktop), so every test
builds its own state by API: a fresh thread per run (unique recipient on a seeded company) and an Inbox holding
only its own draft (every other `review_required` draft is skipped first). Step 1 uploads a CSV with a unique
domain through the CMS import screen; step 2 opens the Intel tab of a seeded company with PSI recordings. The
draft of step 3 comes from the communicator test endpoint, with the company's hooks as its render context
(`@funnel` consumes the CSV-to-draft path on a seed). The send policy is opened to the whole day for each test
(restored after), so drafts are due now: no channel clock in the future, replies land after the sent mail, and
nothing the tests leave behind is sent later by the beat. C07 and C-31 close the window around now first, so
their message waits for a future slot and the beat cannot send it mid-test (the fixture restores the policy). The reply comes from the mailed recipient. Tests marked
`desktop_only` (board, company card, settings, stages) are skipped under E2E_DEVICE.
"""

from __future__ import annotations

import email
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
from entirius_tests.cms_e2e import ADMIN_PASSWORD, ADMIN_USERNAME, API_BASE_URL, module_installed, require_module
from entirius_tests.cms_pages import (
    BoardPage,
    CompanyPage,
    InboxPage,
    LeadsImportPage,
    NotificationBar,
    SettingsPage,
    StagesPage,
    ThreadPage,
)

pytestmark = require_module("leads")

CHANNEL = "default-europe"
COMMUNICATOR = f"api/communicator/v2/admin/{CHANNEL}/"
LEADS = f"api/leads/v2/admin/{CHANNEL}/"
SITEINTEL = f"api/siteintel/v2/admin/{CHANNEL}/"
LEADS_CSV = Path(__file__).resolve().parents[2] / "package" / "leads--default-europe.csv"
INTEL_DOMAIN = "example-shop-5.test"  # PSI recordings (desktop strategy) in fixtures/siteintel
MAIL_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "mail"
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."
MAX_TAPS_TO_ACCEPT = 3
MESSAGE_ID_HEADER = re.compile(rb"^Message-ID: .*$", re.MULTILINE)
DATE_HEADER = re.compile(rb"^Date: .*$", re.MULTILINE)
FROM_HEADER = re.compile(rb"^From: .*$", re.MULTILINE)
OPEN_POLICY = {
    "business_days_only": False,
    "daily_cap": 1000,
    "windows": [{"start_time": "00:00", "end_time": "23:59"}],
}
CLOSED_WINDOW_OFFSET_H = 12
LAPTOP_VIEWPORT = {"width": 1280, "height": 800}


@pytest.fixture
def api() -> ApiClient:
    client = ApiClient(base_url=API_BASE_URL)
    client.set_auth_token(obtain_jwt_token(API_BASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD))
    return client


@pytest.fixture(autouse=True)
def open_send_policy(api: ApiClient):
    policy = _ok(api.get(api.url(f"{COMMUNICATOR}policy/")))
    original = {key: policy[key] for key in ("business_days_only", "daily_cap", "spread", "windows")}
    _ok(api.put(api.url(f"{COMMUNICATOR}policy/"), json={**original, **OPEN_POLICY}))
    yield
    _ok(api.put(api.url(f"{COMMUNICATOR}policy/"), json=original))


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
            "company_name": company["name"],  # the Company column must read as a company, never an internal code
            "body": "E2E funnel draft.",
            "hooks": company["hooks"],
            "platform": company["platform"],
        },
        "subject_ref": f"leads.Company:{company['id']}",
        "requires_review": requires_review,
    }
    return _ok(api.post(api.url(f"{COMMUNICATOR}test/communicate/"), json=body), 201)


def _send(api: ApiClient, message: dict) -> dict:
    """Moves the channel clock to the message's slot (else the policy's next slot — now, under the open policy)
    for one beat run, then clears it; returns the sent message."""
    slot = message.get("scheduled_at") or _ok(api.get(api.url(f"{COMMUNICATOR}policy/")))["next_slot"]
    _ok(clock.set_channel_clock(api, CHANNEL, slot))
    try:
        _ok(clock.run_beat_send(api, CHANNEL))
    finally:
        _ok(clock.clear_channel_clock(api, CHANNEL))
    sent = _ok(api.get(api.url(f"{COMMUNICATOR}messages/?status=sent&page_size=100")))["results"]
    found = [m for m in sent if m["id"] == message["id"]]
    assert found, f"message {message['id']} was not sent"
    return found[0]


def _reply(api: ApiClient, sent: dict, fixture: str) -> None:
    eml = mail.render_fixture(MAIL_FIXTURES / fixture, sent["message_id"])
    written = format_datetime(datetime.fromisoformat(sent["sent_at"]) + timedelta(minutes=1))
    eml = DATE_HEADER.sub(lambda _: f"Date: {written}".encode(), eml, count=1)
    eml = FROM_HEADER.sub(lambda _: f"From: Anna <{sent['thread']['recipient_email']}>".encode(), eml, count=1)
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


def _close_window_around_now(api: ApiClient) -> datetime:
    """One window CLOSED_WINDOW_OFFSET_H hours from now in the channel timezone (the open policy's `next_slot` is
    the channel's now), so an accepted draft is scheduled in the future and the worker cannot send it mid-test."""
    policy = _ok(api.get(api.url(f"{COMMUNICATOR}policy/")))
    now = datetime.fromisoformat(policy["next_slot"])
    hour = (now.hour + CLOSED_WINDOW_OFFSET_H) % 24
    window = {"start_time": f"{hour:02d}:00", "end_time": f"{hour:02d}:59"}
    body = {key: policy[key] for key in ("business_days_only", "daily_cap", "spread")} | {"windows": [window]}
    policy = _ok(api.put(api.url(f"{COMMUNICATOR}policy/"), json=body))
    assert datetime.fromisoformat(policy["next_slot"]) > now, f"window {window} is open at {now}"
    return now


def test_C07_accept_from_inbox_schedules(admin_page: Page, api: ApiClient):
    _clear_review_queue(api)
    draft = _communicate(api, _company(api, "example-shop-4.test"), requires_review=True)
    now = _close_window_around_now(api)
    inbox = _accept_in_inbox(admin_page, draft)
    assert inbox.has_no_horizontal_scroll()
    approved = _ok(api.get(api.url(f"{COMMUNICATOR}review/?status=approved&page_size=100")))["results"]
    accepted = [m for m in approved if m["id"] == draft["id"]]
    assert accepted and accepted[0]["scheduled_at"] and accepted[0]["reviewed_by_id"]
    assert datetime.fromisoformat(accepted[0]["scheduled_at"]) > now, "accepted draft must wait for its slot"
    inbox.expect_empty_with_scheduled()


def _steps_3_to_7(page: Page, api: ApiClient, company: dict) -> None:
    _clear_review_queue(api)
    draft = _communicate(api, company, requires_review=True)  # step 3
    inbox = _accept_in_inbox(page, draft)  # step 4
    assert inbox.taps <= MAX_TAPS_TO_ACCEPT, f"accepting a draft took {inbox.taps} taps"
    approved = _ok(api.get(api.url(f"{COMMUNICATOR}review/?status=approved&page_size=100")))["results"]
    sent = _send(api, next(m for m in approved if m["id"] == draft["id"]))  # step 5
    thread = ThreadPage(page)
    thread.open(company["id"])
    thread.expect_outbound(draft["subject"], "sent")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    _reply(api, sent, "reply_plain.eml")  # step 6
    page.reload()
    thread.expect_reply("can we talk on Thursday")
    InboxPage(page).open()  # step 7 starts away from the company thread: the tap itself must jump there
    bar = NotificationBar(page)
    bar.expect_unread()
    before = bar.unread()
    bar.open()
    bar.open_row(f"Reply from {company['name']}")
    expect(page).to_have_url(re.compile(rf"/leads/companies/{company['id']}(\?|$)"))
    expect(page.get_by_test_id("thread-company")).to_have_text(company["name"], timeout=15000)
    thread.expect_reply("can we talk on Thursday")
    bar.expect_unread_count(before - 1)


def test_funnel_steps_3_to_7(admin_page: Page, api: ApiClient):
    _steps_3_to_7(admin_page, api, _company(api, "example-shop-5.test"))


def _unique_csv(tmp_path: Path) -> tuple[Path, str]:
    """The first row of the package CSV under a unique domain: every run creates its own company in `new`."""
    header, row = LEADS_CSV.read_text().splitlines()[:2]
    domain = f"e2e-{time.time_ns()}.test"
    fields = row.split(",")
    fields[1], fields[7] = domain, f"jan@{domain}"
    path = tmp_path / "leads.csv"
    path.write_text(f"{header}\n{','.join(fields)}\n")
    return path, domain


def _imported_company(api: ApiClient, tmp_path: Path) -> dict:
    path, domain = _unique_csv(tmp_path)
    files = {"file": (path.name, path.read_bytes(), "text/csv")}
    _ok(api.post(api.url(f"{LEADS}test/import-now/"), files=files))
    return _company(api, domain)


def _route_import_to_import_now(page: Page) -> None:
    """Zeno shares no import temp dir between service and worker, so a queued `POST imports/` fails
    `missing_file`; the CMS upload is redirected to the development `test/import-now/` (same multipart body)."""

    def redirect(route):
        if route.request.method != "POST":
            return route.continue_()
        return route.continue_(url=route.request.url.replace("/imports/", "/test/import-now/"))

    page.route("**/imports/", redirect)


def _audited(api: ApiClient, company: dict) -> None:
    audit = _ok(api.post(api.url(f"{LEADS}companies/{company['id']}/request-audit/")), 202)
    if audit["status"] in ("pending", "running"):
        run = api.post(api.url(f"{SITEINTEL}test/run-now/{audit['audit_id']}/"))
        assert run.ok, f"run-now {audit['audit_id']}: {run.status_code} {run.text}"


@pytest.mark.desktop_only
def test_funnel_steps_1_to_7(admin_page: Page, api: ApiClient, tmp_path: Path):
    csv_path, domain = _unique_csv(tmp_path)
    _route_import_to_import_now(admin_page)
    LeadsImportPage(admin_page).upload(csv_path)  # step 1
    board = BoardPage(admin_page)
    board.open()
    board.search(domain)
    expect(board.card("new", domain)).to_be_visible(timeout=15000)
    company = _company(api, INTEL_DOMAIN)  # step 2
    _audited(api, company)
    card = CompanyPage(admin_page)
    card.open(company["id"])
    card.open_tab("intel")
    expect(admin_page.get_by_test_id("intel-score-desktop")).to_contain_text("/ 100", timeout=15000)
    _steps_3_to_7(admin_page, api, company)


@pytest.mark.desktop_only
def test_L15_create_customer_action_only_with_accounts(admin_page: Page, api: ApiClient, tmp_path: Path):
    company = _imported_company(api, tmp_path)
    card = CompanyPage(admin_page)
    card.open(company["id"])
    expect(card.create_customer_button()).to_have_count(0)
    stages = _ok(api.get(api.url(f"{LEADS}stages/")))["results"]
    won = next(stage for stage in stages if stage["kind"] == "won")
    _ok(api.post(api.url(f"{LEADS}companies/{company['id']}/transition/"), json={"stage_key": won["key"]}))
    card.open(company["id"])
    if module_installed("accounts"):
        expect(card.create_customer_button()).to_be_visible()
    else:
        expect(card.create_customer_button()).to_have_count(0)


@pytest.mark.desktop_only
def test_C31_send_now_moves_scheduled_at(admin_page: Page, api: ApiClient):
    admin_page.set_viewport_size(LAPTOP_VIEWPORT)  # the laptop a salesperson works on, sidebar open (FIX-17a item 1)
    now = _close_window_around_now(api)  # a closed window: the beat defers the message, it cannot race the asserts
    company = _company(api, "example-shop-6.test")
    draft = _communicate(api, company, requires_review=True)
    _ok(api.post(api.url(f"{COMMUNICATOR}review/{draft['id']}/accept/"), json={}))  # accepting sets the slot
    before = _waiting_message(api, draft["id"])
    assert datetime.fromisoformat(before["scheduled_at"]) > now, "the message must wait for a future slot"
    recipient = before["thread"]["recipient_email"]
    mailbox = _mails_to(recipient)
    settings = SettingsPage(admin_page)
    settings.open()
    placement = settings.send_now_placement(before["id"])
    assert placement["sidebar_open"], f"the sidebar must be open for this check: {placement['box']}"
    assert placement["on_screen"], f"Send now is clipped away at 1280 px: {placement['box']}"
    settings.expect_company(before["id"], company["name"])
    # The window is closed: the row names its hours, not the current minute nor a clock (FIX-17b item 14).
    settings.expect_waiting_for_window(before["id"], _window_hours(api))
    settings.send_now(before["id"])
    admin_page.reload()  # the state comes from the row's own data, so it survives a reload (FIX-17 item 10)
    settings.expect_queued_asap(before["id"])
    after = _waiting_message(api, before["id"])
    assert datetime.fromisoformat(after["scheduled_at"]) < datetime.fromisoformat(before["scheduled_at"])
    unchanged = {key: value for key, value in before.items() if key != "scheduled_at"}
    assert {key: after[key] for key in unchanged} == unchanged, "Send now must move scheduled_at only"
    assert _mails_to(recipient) == mailbox, "Send now must not send — the beat does"
    _open_window(api)  # restore the open policy before the beat run: now the message is sent
    _send(api, after)
    assert _wait_for_mails_to(recipient, mailbox + 1) == mailbox + 1


def _window_hours(api: ApiClient) -> str:
    windows = _ok(api.get(api.url(f"{COMMUNICATOR}policy/")))["windows"]
    return ", ".join(f"{w['start_time'][:5]}–{w['end_time'][:5]}" for w in windows)


def _open_window(api: ApiClient) -> None:
    policy = _ok(api.get(api.url(f"{COMMUNICATOR}policy/")))
    body = {key: policy[key] for key in ("business_days_only", "daily_cap", "spread", "windows")} | OPEN_POLICY
    _ok(api.put(api.url(f"{COMMUNICATOR}policy/"), json=body))


def _waiting_message(api: ApiClient, message_id: int) -> dict:
    found = [m for m in _waiting_messages(api) if m["id"] == message_id]
    assert found, f"message {message_id} is not waiting (approved or scheduled)"
    return found[0]


def _mails_to(recipient: str) -> int:
    """Sandbox mails addressed to one recipient (the sandbox keeps the real address in X-Original-To)."""
    headers = (email.message_from_string(m["mimeMessage"])["X-Original-To"] for m in mail.list_messages())
    return sum(1 for original in headers if original == recipient)


def _wait_for_mails_to(recipient: str, n: int, timeout: float = 20) -> int:
    deadline = time.monotonic() + timeout
    while (current := _mails_to(recipient)) < n and time.monotonic() < deadline:
        time.sleep(0.5)
    return current


def _waiting_messages(api: ApiClient) -> list[dict]:
    statuses = ("approved", "scheduled")
    pages = [_ok(api.get(api.url(f"{COMMUNICATOR}messages/?status={s}&page_size=100"))) for s in statuses]
    return [message for page in pages for message in page["results"]]


@pytest.mark.desktop_only
def test_L18_stage_delete_refused_inline(admin_page: Page, api: ApiClient, tmp_path: Path):
    stage = _ok(
        api.post(
            api.url(f"{LEADS}stages/"), json={"key": f"e2e-hold-{time.time_ns()}", "label": "E2E hold", "order": 900}
        ),
        201,
    )
    company = _imported_company(api, tmp_path)
    try:
        _ok(api.post(api.url(f"{LEADS}companies/{company['id']}/transition/"), json={"stage_key": stage["key"]}))
        stages = StagesPage(admin_page)
        stages.open()
        stages.delete(stage["key"])
        expect(stages.row(stage["key"]).get_by_test_id("stage-error")).to_be_visible(timeout=15000)
        assert any(row["key"] == stage["key"] for row in _ok(api.get(api.url(f"{LEADS}stages/")))["results"])
    finally:
        _drop_stage(api, stage, company)


def _drop_stage(api: ApiClient, stage: dict, company: dict) -> None:
    """The hold stage exists for this test only — left behind it is test noise on every later Stages and Board
    screen (and in the acceptance run). Its company goes back to the first stage, then the stage goes."""
    first = _ok(api.get(api.url(f"{LEADS}stages/")))["results"][0]
    _ok(api.post(api.url(f"{LEADS}companies/{company['id']}/transition/"), json={"stage_key": first["key"]}))
    assert api.delete(api.url(f"{LEADS}stages/{stage['id']}/")).status_code == 204


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
    # The CMS names the company in the communicator's medium "Reply from <address>" row too — N-01 is the high one.
    expect(bar.row(f"Reply from {company['name']}", severity="high")).to_be_visible()
    bar.open_row(f"Reply from {company['name']}")
    expect(admin_page.get_by_test_id("thread-company")).to_have_text(company["name"])
