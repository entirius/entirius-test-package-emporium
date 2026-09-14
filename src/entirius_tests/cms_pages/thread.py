# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads company thread (`/leads/companies/<id>`): chat timeline with sent mail, replies and notes."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000


class ThreadPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.taps = 0

    def open(self, company_id: int) -> None:
        self.page.goto(f"{CMS_BASE_URL}/leads/companies/{company_id}")
        expect(self.page.get_by_test_id("thread-timeline")).to_be_visible(timeout=TIMEOUT_MS)

    def expect_outbound(self, subject: str, status: str) -> None:
        bubble = self.page.get_by_test_id("timeline-out").filter(has_text=subject).last
        expect(bubble.get_by_test_id(f"status-{status}")).to_be_visible(timeout=TIMEOUT_MS)

    def expect_reply(self, text: str) -> None:
        expect(self.page.get_by_test_id("timeline-in").filter(has_text=text).last).to_be_visible(timeout=TIMEOUT_MS)

    def confirm_optout(self) -> None:
        self.taps += 1
        self.page.get_by_test_id("confirm-optout").last.click()
        expect(self.page.get_by_text("Opt-out confirmed").last).to_be_visible(timeout=TIMEOUT_MS)
