# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads stages admin (`/leads/stages`): ordered rows, delete refused inline while companies sit in a stage."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000


class StagesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.taps = 0

    def open(self) -> None:
        self.page.goto(f"{CMS_BASE_URL}/leads/stages")
        expect(self.page.get_by_test_id("stage-row").first).to_be_visible(timeout=TIMEOUT_MS)

    def row(self, key: str) -> Locator:
        return self.page.locator(f'[data-testid="stage-row"][data-stage="{key}"]')

    def delete(self, key: str) -> None:
        self.taps += 1
        self.row(key).get_by_test_id("stage-delete").click()
