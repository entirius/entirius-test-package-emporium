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
        # The desktop company card opens on its timeline tab; a phone gets the thread alone either way.
        self.page.goto(f"{CMS_BASE_URL}/leads/companies/{company_id}?tab=timeline")
        # `.first` = the newest thread; an older thread with a reply expands "Earlier threads" with its own timeline.
        expect(self.page.get_by_test_id("thread-timeline").first).to_be_visible(timeout=TIMEOUT_MS)

    def expect_outbound(self, subject: str, status: str) -> None:
        bubble = self.page.get_by_test_id("timeline-out").filter(has_text=subject).last
        expect(bubble.get_by_test_id(f"status-{status}")).to_be_visible(timeout=TIMEOUT_MS)

    def expect_reply(self, text: str) -> None:
        expect(self.page.get_by_test_id("timeline-in").filter(has_text=text).last).to_be_visible(timeout=TIMEOUT_MS)

    def confirm_optout(self) -> None:
        """Confirms the newest unconfirmed opt-out of the newest thread; older threads stay behind "Earlier threads"."""
        self.taps += 1
        buttons = self.page.get_by_test_id("confirm-optout")
        expect(buttons.last).to_be_visible(timeout=TIMEOUT_MS)
        pending = buttons.count()
        buttons.last.click()
        expect(buttons).to_have_count(pending - 1, timeout=TIMEOUT_MS)
