# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Communicator send settings (`/communicator/settings`): waiting messages with Send now.

A mail already sitting at the channel clock cannot be pulled earlier, so its row offers no second Send now;
the departure column states the slot the send policy will use, never a clock that slides with the minute."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000
SIDEBAR_OPEN_PX = 200  # the CMS sidebar is 300 px open, 64 px collapsed


class SettingsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.taps = 0

    def open(self) -> None:
        self.page.goto(f"{CMS_BASE_URL}/communicator/settings")
        expect(self.page.get_by_test_id("settings-scheduled")).to_be_visible(timeout=TIMEOUT_MS)

    def row(self, message_id: int):
        return self.page.locator(f'[data-testid="scheduled-row"][data-message="{message_id}"]')

    def send_now(self, message_id: int) -> None:
        row = self.row(message_id)
        self.taps += 1
        row.get_by_test_id("scheduled-send-now").click()
        expect(row.get_by_test_id("scheduled-asap")).to_be_visible(timeout=TIMEOUT_MS)

    def expect_queued_asap(self, message_id: int) -> None:
        """After a reload the row still says the mail is as early as it can be, and offers no second Send now."""
        row = self.row(message_id)
        expect(row.get_by_test_id("scheduled-asap")).to_be_visible(timeout=TIMEOUT_MS)
        expect(row.get_by_test_id("scheduled-send-now")).to_have_count(0)

    def expect_waiting_for_window(self, message_id: int, hours: str) -> None:
        """A closed window is a state with its hours (`08:00–17:00`), never a clock that the policy may not keep."""
        state = self.row(message_id).get_by_test_id("scheduled-state")
        expected = rf"^waiting for the send window \({re.escape(hours)}\)$"
        expect(state).to_have_text(re.compile(expected), timeout=TIMEOUT_MS)

    def expect_company(self, message_id: int, name: str) -> None:
        expect(self.row(message_id)).to_contain_text(name, timeout=TIMEOUT_MS)

    def send_now_placement(self, message_id: int) -> dict:
        """Where the row's Send now sits, for the caller to assert: the content column clips what runs past its
        right edge (`overflow: hidden`), so a table wider than it hides the action with no hint at all."""
        expect(self.row(message_id).get_by_test_id("scheduled-send-now")).to_be_visible(timeout=TIMEOUT_MS)
        return self.page.evaluate(
            """({id, open}) => {
                const button = document.querySelector(
                    `[data-testid="scheduled-row"][data-message="${id}"] [data-testid="scheduled-send-now"]`
                );
                const box = button.getBoundingClientRect();
                const sidebar = document.querySelector('[data-testid="app-sidebar"]');
                const width = sidebar ? sidebar.getBoundingClientRect().width : 0;
                return {
                    on_screen: box.left >= 0 && box.right <= window.innerWidth,
                    sidebar_open: width >= open,
                    box: {left: box.left, right: box.right, viewport: window.innerWidth, sidebar: width},
                };
            }""",
            {"id": message_id, "open": SIDEBAR_OPEN_PX},
        )
