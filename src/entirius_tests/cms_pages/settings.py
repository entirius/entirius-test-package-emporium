# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Communicator send settings (`/communicator/settings`): waiting messages with Send now.

A sent-now row is marked due from its own data (its slot is now or past), so the marker survives a reload."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000


class SettingsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.taps = 0

    def open(self) -> None:
        self.page.goto(f"{CMS_BASE_URL}/communicator/settings")
        expect(self.page.get_by_test_id("settings-scheduled")).to_be_visible(timeout=TIMEOUT_MS)

    def send_now(self, message_id: int) -> None:
        row = self.page.locator(f'[data-testid="scheduled-row"][data-message="{message_id}"]')
        self.taps += 1
        row.get_by_test_id("scheduled-send-now").click()
        expect(row.get_by_test_id("scheduled-due")).to_be_visible(timeout=TIMEOUT_MS)

    def expect_due(self, message_id: int) -> None:
        """After a reload the row still shows it is due and offers no second Send now."""
        row = self.page.locator(f'[data-testid="scheduled-row"][data-message="{message_id}"]')
        expect(row.get_by_test_id("scheduled-due")).to_be_visible(timeout=TIMEOUT_MS)
        expect(row.get_by_test_id("scheduled-send-now")).to_have_count(0)
