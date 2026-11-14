# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads Today (`/leads/today`): the caller's open tasks, one row per task (`data-task`), and the task dialog."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000


class TodayPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self) -> None:
        self.page.goto(f"{CMS_BASE_URL}/leads/today")
        expect(self.page.get_by_test_id("leads-today")).to_be_visible(timeout=TIMEOUT_MS)

    def task(self, task_id: int) -> Locator:
        return self.page.locator(f'[data-testid="task-row"][data-task="{task_id}"]')

    def open_subject(self, task_id: int) -> None:
        """The task's title and its subject both link to the subject; a phone card shows the title only."""
        self.task(task_id).get_by_role("link").first.click()


class TaskDialog:
    """The dialog behind every `task-done` button (Today, the company and the deal tabs)."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def close_with(self, row: Locator, outcome: str) -> None:
        row.get_by_test_id("task-done").click()
        dialog = self.page.get_by_test_id("task-dialog")
        dialog.get_by_test_id("task-outcome").locator("textarea").fill(outcome)
        dialog.get_by_test_id("task-submit").click()
        expect(dialog).to_be_hidden(timeout=TIMEOUT_MS)
