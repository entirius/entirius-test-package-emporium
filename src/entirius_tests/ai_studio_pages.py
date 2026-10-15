# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CMS screens the AI studio e2e shares: the product AI drawer and the product-list AI bulk action.

Selectors are the CMS `data-testid`s where they exist; the AI trigger, the template buttons and the bulk action
have none and are found by role and visible text.
"""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL

# Seeded product template labels (service fixtures/common/enrichment_workers.json).
META_TEMPLATE = "Meta opisy"
DESCRIPTION_TEMPLATE = "Opis produktu"
SEO_RESEARCH = "Search research (what people search for, what ranks)"
AI_TIMEOUT = 90_000
# A "/" ends a regex in Playwright's selector syntax, so it is escaped.
_AI_TRIGGER = re.compile(r"^AI \/ Enricher")
# The run dialog's two actions: the express lane and the normal queue.
RUN_NOW = "ai-task-run-now"
ADD_TO_QUEUE = "ai-task-add-to-queue"


def ai_trigger(page: Page) -> Locator:
    """The product page's "AI / Enricher" button; its name carries the count to review."""
    return page.get_by_role("button", name=_AI_TRIGGER)


def open_drawer(page: Page) -> Locator:
    """The product's AI drawer; a run started from it opens it again by itself (on that run)."""
    drawer = page.get_by_test_id("ai-results-drawer")
    if not drawer.is_visible():
        ai_trigger(page).click()
    expect(drawer).to_be_visible()
    return drawer


def run_template(page: Page, drawer: Locator, label: str, *, lane: str = RUN_NOW) -> None:
    """Template button in the drawer → the run dialog with its presets → Run now (or Add to queue)."""
    drawer.get_by_role("button", name=label, exact=True).click()
    page.get_by_test_id("ai-task-dialog").get_by_test_id(lane).click()


def proposal_card(page: Page, drawer: Locator, field: str, language: str) -> Locator:
    """The drawer card of one field in one language (`EN`, `PL`, …)."""
    return (
        drawer.locator("article")
        .filter(has=page.get_by_role("heading", name=field, exact=True))
        .filter(has=page.get_by_test_id("proposal-language").get_by_text(language, exact=True))
    )


def bulk_run(page: Page, skus: list[str], template: str, *, research: bool = False) -> int:
    """Product list: select the products → AI → template (+ SEO research) → Add to queue; the created task's id."""
    dialog = open_bulk_dialog(page, skus, template)
    if research:
        dialog.get_by_role("checkbox", name=SEO_RESEARCH).check()
    dialog.get_by_test_id(ADD_TO_QUEUE).click()
    run = dialog.get_by_test_id("ai-task-link")
    expect(run).to_have_attribute("href", re.compile(r"/enrichment/runs\?task=\d+$"))
    return int(re.search(r"task=(\d+)", run.get_attribute("href") or "").group(1))


def open_bulk_dialog(page: Page, skus: list[str], template: str) -> Locator:
    """Product list: select the products → AI → template; the run dialog."""
    page.goto(f"{CMS_BASE_URL}/pim/products")
    page.get_by_role("textbox", name="Start typing...").fill(_common_prefix(skus))
    for sku in skus:
        row = page.get_by_role("row").filter(has=page.get_by_role("gridcell", name=sku, exact=True))
        row.get_by_role("checkbox").check()
    page.get_by_role("combobox", name="AI").click()
    page.get_by_role("option", name=template, exact=True).click()
    dialog = page.get_by_test_id("ai-task-dialog")
    expect(dialog).to_be_visible()
    return dialog


def _common_prefix(skus: list[str]) -> str:
    prefix = skus[0]
    while not all(sku.startswith(prefix) for sku in skus):
        prefix = prefix[:-1]
    return prefix
