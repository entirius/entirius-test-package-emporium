# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads deals: the deal dialog on the company card, the deal card (`/leads/deals/<id>`) and the board
(`/leads/deals/board`, desktop) with one column per stage (`data-stage`)."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

TIMEOUT_MS = 15000


class DealDialog:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open_deal(self, title: str) -> None:
        self.page.get_by_test_id("company-open-deal").click()
        dialog = self.page.get_by_test_id("deal-dialog")
        dialog.get_by_test_id("deal-dialog-title").locator("input").fill(title)
        dialog.get_by_test_id("deal-dialog-submit").click()
        expect(self.page.get_by_test_id("leads-deal")).to_be_visible(timeout=TIMEOUT_MS)


class DealCardPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def move_to(self, stage_label: str) -> None:
        self.page.get_by_test_id("deal-move-stage").click()
        self.page.get_by_role("option", name=stage_label, exact=True).click()

    def expect_stage(self, stage_label: str) -> None:
        expect(self.page.get_by_test_id("deal-move-stage")).to_contain_text(stage_label, timeout=TIMEOUT_MS)


class DealsBoardPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self) -> None:
        self.page.goto(f"{CMS_BASE_URL}/leads/deals/board")
        expect(self.page.get_by_test_id("deals-board-columns")).to_be_visible(timeout=TIMEOUT_MS)

    def column(self, stage_key: str) -> Locator:
        return self.page.locator(f'[data-testid="deals-column"][data-stage="{stage_key}"]')

    def card(self, deal_id: int) -> Locator:
        return self.page.locator(f'[data-testid="deal-card"][data-deal="{deal_id}"]')

    def drag(self, deal_id: int, stage_key: str) -> None:
        """Mouse steps by the card's title into the column's card list: the board's sortable runs in fallback mode
        and starts a drag only after the pointer moved a little; `drag_to` does not start it."""
        expect(self.card(deal_id)).to_be_visible(timeout=TIMEOUT_MS)
        source = self.card(deal_id).bounding_box()
        target = self.column(stage_key).locator(".column__cards").bounding_box()
        mouse, x, y = self.page.mouse, source["x"] + 40, source["y"] + 30
        mouse.move(x, y)
        mouse.down()
        mouse.move(x + 10, y + 10, steps=5)
        mouse.move(target["x"] + 100, target["y"] + 30, steps=30)
        mouse.move(target["x"] + 101, target["y"] + 31, steps=2)
        mouse.up()
