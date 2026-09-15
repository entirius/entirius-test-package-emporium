# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared CMS notification bar: bell with the unread badge, list, one tap to read and jump."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

TIMEOUT_MS = 15000
POLL_MS = 35000  # the bar polls every 30 s


class NotificationBar:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.taps = 0

    def expect_unread(self) -> None:
        expect(self.page.get_by_test_id("notif-count")).to_be_visible(timeout=POLL_MS)

    def unread(self) -> int:
        """The badge number; 0 when the badge is hidden."""
        badge = self.page.get_by_test_id("notif-count")
        return int(badge.inner_text()) if badge.is_visible() else 0

    def expect_unread_count(self, count: int) -> None:
        badge = self.page.get_by_test_id("notif-count")
        if count:
            expect(badge).to_have_text(str(count), timeout=TIMEOUT_MS)
        else:
            expect(badge).to_be_hidden(timeout=TIMEOUT_MS)

    def row(self, title: str, severity: str = "") -> Locator:
        rows = self.page.locator(f'[data-testid="notif-row"]{f".notif-row--{severity}" if severity else ""}')
        return rows.filter(has_text=title).first

    def open(self) -> None:
        self.taps += 1
        self.page.get_by_test_id("notif-bell").click()
        expect(self.page.get_by_test_id("notif-list")).to_be_visible(timeout=TIMEOUT_MS)

    def open_row(self, title: str) -> None:
        self.taps += 1
        self.row(title).click()
        expect(self.page.get_by_test_id("leads-thread")).to_be_visible(timeout=TIMEOUT_MS)
