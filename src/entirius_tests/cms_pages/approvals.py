# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads approvals (`/leads/approvals`, desktop): drafts of every channel, one row per draft (`data-approval`),
bulk approve and reject."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000


class ApprovalsPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self, search: str) -> None:
        self.page.goto(f"{CMS_BASE_URL}/leads/approvals")
        expect(self.page.get_by_test_id("leads-approvals")).to_be_visible(timeout=TIMEOUT_MS)
        self.page.get_by_test_id("approvals-search").locator("input").fill(search)

    def row(self, message_id: int) -> Locator:
        return self.page.locator(f'[data-testid="approval-row"][data-approval="{message_id}"]')

    def approve(self, message_ids: list[int]) -> None:
        for message_id in message_ids:
            self.row(message_id).get_by_role("checkbox").check()
        self.page.get_by_test_id("approvals-approve").click()
        for message_id in message_ids:
            expect(self.row(message_id)).to_be_hidden(timeout=TIMEOUT_MS)
