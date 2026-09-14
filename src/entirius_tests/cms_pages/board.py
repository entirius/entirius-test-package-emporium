# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads stage board (`/leads/board`): one column per stage, company cards."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000


class BoardPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.taps = 0

    def open(self) -> None:
        self.page.goto(f"{CMS_BASE_URL}/leads/board")
        expect(self.page.get_by_test_id("board-column").first).to_be_visible(timeout=TIMEOUT_MS)

    def card(self, stage_key: str, domain: str) -> Locator:
        column = self.page.locator(f'[data-testid="board-column"][data-stage="{stage_key}"]')
        return column.locator(f'[data-testid="board-card"][data-company="{domain}"]')

    def search(self, text: str) -> None:
        self.taps += 1
        self.page.get_by_test_id("board-search").fill(text)
        self.page.get_by_test_id("board-search").press("Enter")

    def open_card(self, stage_key: str, domain: str) -> None:
        self.taps += 1
        self.card(stage_key, domain).get_by_role("link", name=domain).click()
        expect(self.page.get_by_test_id("company-card")).to_be_visible(timeout=TIMEOUT_MS)
