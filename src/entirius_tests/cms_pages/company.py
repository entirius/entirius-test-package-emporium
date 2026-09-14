# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads company card on desktop (`/leads/companies/<id>?tab=`): header, actions, tabs."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000


class CompanyPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.taps = 0

    def open(self, company_id: int, tab: str = "overview") -> None:
        self.page.goto(f"{CMS_BASE_URL}/leads/companies/{company_id}?tab={tab}")
        expect(self.page.get_by_test_id("company-actions")).to_be_visible(timeout=TIMEOUT_MS)

    def open_tab(self, tab: str) -> None:
        self.taps += 1
        self.page.get_by_test_id(f"company-tab-{tab}").click()

    def create_customer_button(self) -> Locator:
        return self.page.get_by_test_id("company-create-customer")
