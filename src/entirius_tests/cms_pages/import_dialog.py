# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads CSV import (`/leads/import`): pick a file, upload, wait for the batch report."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 30000


class LeadsImportPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.taps = 0

    def upload(self, csv_path: Path) -> None:
        self.page.goto(f"{CMS_BASE_URL}/leads/import")
        self.page.get_by_test_id("import-file").set_input_files(str(csv_path))
        self.taps += 1
        self.page.get_by_test_id("import-upload").click()
        expect(self.page.get_by_test_id("import-status")).to_have_text("done", timeout=TIMEOUT_MS)
