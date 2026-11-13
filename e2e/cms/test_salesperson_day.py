# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A salesperson's day in the CMS Leads panel, on a phone and on a desktop (`E2E_DEVICE`): Today -> the task's
company -> read the reply -> write a mail by hand -> close the task with an outcome -> open a deal -> move it. The
desktop adds the bulk approval of two drafts and a drag on the deal board.

Setup through the API (`entirius_tests.crm_e2e`): the admin's own company per test, its first mail sent on the
reference-week channel clock, an interested reply through the development endpoint (no toolbox). Needs the CMS of
the CRM release (`make cms-dev`), `make mail` and the seed's CRM configuration; re-runnable on one database."""

from __future__ import annotations

import time

import pytest
from playwright.sync_api import Page, expect

from entirius_tests import crm_e2e
from entirius_tests.ai_studio_e2e import AdminApi, service_api, wait_for
from entirius_tests.cms_e2e import require_module
from entirius_tests.cms_pages.approvals import ApprovalsPage
from entirius_tests.cms_pages.company import CompanyPage
from entirius_tests.cms_pages.deals import DealCardPage, DealDialog, DealsBoardPage
from entirius_tests.cms_pages.today import TaskDialog, TodayPage

pytestmark = [require_module("leads"), require_module("todo")]
TIMEOUT_MS = 15000


@pytest.fixture
def api():
    api = service_api()
    crm_e2e.freeze_clock(api)
    yield api
    crm_e2e.clear_clock(api)


def deal_id(page: Page) -> int:
    return int(page.url.rstrip("/").split("/")[-1])


def test_salesperson_day(admin_page: Page, api: AdminApi) -> None:
    day = crm_e2e.salesperson_day(api)
    today = TodayPage(admin_page)
    today.open()
    expect(today.task(day["task"])).to_be_visible(timeout=TIMEOUT_MS)
    today.open_subject(day["task"])
    company = CompanyPage(admin_page)
    company.expect_open()
    company.open_tab("timeline")
    expect(company.timeline_entry("reply received")).to_be_visible(timeout=TIMEOUT_MS)
    company.write_mail("BDD a word by hand", "Thank you, the offer follows tomorrow.")
    company.open_tab("tasks")
    TaskDialog(admin_page).close_with(company.task(day["task"]), "talked, offer tomorrow")
    expect(company.task(day["task"])).to_be_hidden(timeout=TIMEOUT_MS)
    company.open_tab("deals")
    DealDialog(admin_page).open_deal("BDD e2e rollout")
    card = DealCardPage(admin_page)
    card.move_to("Proposal")
    card.expect_stage("Proposal")


@pytest.mark.desktop_only
def test_bulk_approval_and_board_drag(admin_page: Page, api: AdminApi) -> None:
    run, owner = str(time.time_ns()), crm_e2e.salesperson_day(api)
    companies = [crm_e2e.import_company(api, f"{run}-{n}", None) for n in range(2)]
    drafts = [crm_e2e.draft(api, company) for company in companies]
    approvals = ApprovalsPage(admin_page)
    approvals.open(f"bdd-e2e-{run}")
    approvals.approve(drafts)
    company = CompanyPage(admin_page)
    company.open(owner["company"], tab="deals")
    DealDialog(admin_page).open_deal("BDD e2e board")
    opened = deal_id(admin_page)
    # A column lists its oldest cards first: the deal starts at the top of a column the BDD runs leave empty.
    api.post(f"{crm_e2e.LEADS}deals/{opened}/transition/", {"stage_key": "negotiation"})
    board = DealsBoardPage(admin_page)
    board.open()
    board.drag(opened, "proposal")
    assert wait_for(lambda: api.get(f"{crm_e2e.LEADS}deals/{opened}/")["stage"]["key"] == "proposal", timeout=15)
    api.post(f"{crm_e2e.TODO}tasks/{owner['task']}/cancel/", {"reason": "e2e cleanup"})
