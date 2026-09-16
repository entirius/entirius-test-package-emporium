# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads Inbox and Review screens (`/leads/inbox`, `/leads/inbox/<id>`)."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000


class InboxPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.taps = 0

    def open(self) -> None:
        """Navigation into the Inbox — not a tap."""
        self.page.goto(f"{CMS_BASE_URL}/leads/inbox")
        # The summary line only exists while drafts wait; an empty queue shows the empty state instead.
        expect(self.page.get_by_test_id("inbox-summary").or_(self.page.get_by_test_id("inbox-empty"))).to_be_visible(
            timeout=TIMEOUT_MS
        )

    def open_draft(self, subject: str) -> None:
        self.taps += 1
        self.page.get_by_test_id("inbox-item").filter(has_text=subject).first.click()
        expect(self.page.get_by_test_id("review-subject")).to_be_visible(timeout=TIMEOUT_MS)

    def send(self) -> None:
        self.taps += 1
        self.page.get_by_test_id("review-send").click()

    def expect_scheduled(self) -> None:
        expect(self.page.get_by_test_id("review-scheduled")).to_be_visible(timeout=TIMEOUT_MS)

    def expect_empty_with_scheduled(self) -> None:
        empty = self.page.get_by_test_id("inbox-empty")
        expect(empty).to_be_visible(timeout=TIMEOUT_MS)
        # the tests close the send window: a closed window names its hours, never a clock (FIX-17b item 14)
        expect(empty).to_contain_text("scheduled, waiting for the send window (")

    def has_no_horizontal_scroll(self) -> bool:
        return self.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
