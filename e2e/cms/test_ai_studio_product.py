# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio in the CMS, scenarios 1-2 (product writer): the product drawer and the bulk run with the Review list.

The toolbox serves fake models only: every answer is a "Lorem ipsum …" placeholder, so the tests check the flow
(cards, versions, apply, batch correction) and the call counts in the toolbox tracker, never the wording.
Each test rejects what an earlier run left pending on its products first, so it re-runs on one seed.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Locator, Page, expect

from entirius_tests import ai_studio_e2e as studio
from entirius_tests import ai_studio_pages as pages
from entirius_tests.cms_e2e import CMS_BASE_URL, require_module

pytestmark = [require_module("enrichment"), pytest.mark.desktop_only]

DRAWER_SKU = "ENT-S001"
BULK_SKUS = ["ENT-C001", "ENT-C002", "ENT-C003"]
UNSAVED_NAME = "Orion Command Sofa (unsaved e2e edit)"
BATCH_INSTRUCTION = "Mention the five-year frame warranty."
COMPACT_ROW_MAX_PX = 80


@pytest.fixture
def drawer_product(enrichment_api: studio.AdminApi):
    """ENT-S001 with nothing pending; its EN meta description is put back after the test (the test applies one)."""
    studio.reject_pending(enrichment_api, DRAWER_SKU)
    original = studio.product(DRAWER_SKU)["meta_description_t9n"]
    yield DRAWER_SKU
    studio.patch_product(DRAWER_SKU, {"meta_description_t9n": original})


def test_product_drawer_correct_restore_apply(
    admin_page: Page, enrichment_api: studio.AdminApi, tracker_api: studio.AdminApi, drawer_product: str
):
    page = admin_page
    languages = studio.channel_languages()
    before = studio.latest_task_id(enrichment_api, drawer_product)
    page.goto(f"{CMS_BASE_URL}/pim/products/{drawer_product}")
    page.get_by_role("textbox", name="Name (EN)").fill(UNSAVED_NAME)
    page.get_by_role("tab", name="SEO").click()

    pages.run_template(page, pages.open_drawer(page), pages.META_TEMPLATE)
    expect(page.get_by_text("AI task started")).to_be_visible()
    expect(page.get_by_text("AI task finished")).to_be_visible(timeout=pages.AI_TIMEOUT)
    task_id = studio.latest_task_id(enrichment_api, drawer_product)
    assert task_id > before
    studio.wait_task_finished(enrichment_api, task_id)
    cards = 2 * len(languages)  # meta title + meta description per channel language
    expect(pages.ai_trigger(page)).to_have_accessible_name(re.compile(f"{cards} to review"))

    drawer = pages.open_drawer(page)
    expect(drawer.locator("article")).to_have_count(cards)
    expect(drawer.get_by_test_id("proposal-cost")).to_have_count(cards)
    studio.shoot(page, "01-product-drawer")

    card = pages.proposal_card(page, drawer, "Meta description", "EN")
    first_text = studio.revisions(enrichment_api, _card_id(card))[0]["value"]["text"]
    _shorten_and_restore(page, card)
    card.get_by_test_id("proposal-accept").click()
    expect(page.get_by_text("Proposal accepted.")).to_be_visible()

    expect(page.get_by_role("textbox", name="Meta Description (EN)")).to_have_value(first_text)
    expect(page.get_by_role("textbox", name="Name (EN)")).to_have_value(UNSAVED_NAME)
    studio.shoot(page, "01-product-applied", page.get_by_role("textbox", name="Meta Description (EN)"))
    assert len(studio.task_calls(tracker_api, task_id, "enrichment.write.meta")) == len(languages)
    assert len(studio.task_calls(tracker_api, task_id, "enrichment.revise")) == 1


def _card_id(card: Locator) -> int:
    href = card.get_by_test_id("open-editor").get_attribute("href") or ""
    return int(href.rstrip("/").rsplit("/", 1)[-1])


def _shorten_and_restore(page: Page, card: Locator) -> None:
    """Quick action "Shorter" → version 2 with its changes → restore version 1 (version 3 = a copy of 1)."""
    card.get_by_test_id("correction-toggle").click()
    card.get_by_test_id("correction-quick-shorten").click()
    expect(card.get_by_test_id("correction-busy")).to_be_hidden(timeout=pages.AI_TIMEOUT)
    card.get_by_test_id("versions-toggle").click()
    expect(card.get_by_test_id("version-2")).to_be_visible()
    card.get_by_test_id("version-toggle-2").click()
    expect(card.get_by_test_id("version-2").get_by_test_id("text-diff")).to_be_visible()
    studio.shoot(page, "01-product-versions", card)
    card.get_by_test_id("version-restore-1").click()
    expect(page.get_by_text("Version restored.")).to_be_visible()
    expect(card.get_by_test_id("version-3")).to_be_visible()


@pytest.fixture
def bulk_products(enrichment_api: studio.AdminApi) -> list[str]:
    for sku in BULK_SKUS:
        studio.reject_pending(enrichment_api, sku)
    return BULK_SKUS


def test_bulk_run_review_and_correct_all(
    admin_page: Page, enrichment_api: studio.AdminApi, tracker_api: studio.AdminApi, bulk_products: list[str]
):
    page = admin_page
    expected = len(bulk_products) * len(studio.channel_languages())  # one description per product × language
    task_id = pages.bulk_run(page, bulk_products, pages.DESCRIPTION_TEMPLATE)
    studio.wait_task_finished(enrichment_api, task_id)

    page.goto(f"{CMS_BASE_URL}/enrichment?task={task_id}")
    expect(page.get_by_test_id("enrichment-count")).to_contain_text(str(expected))
    rows = page.get_by_role("main").get_by_role("row").filter(has=page.get_by_role("button", name="Open"))
    expect(rows).to_have_count(expected)
    _assert_compact(rows)
    studio.shoot(page, "02-review-list")

    proposals = studio.task_proposals(enrichment_api, task_id)
    _open_detail(page, proposals[0]["id"])
    studio.shoot(page, "02-review-detail")
    page.keyboard.press("Escape")

    _correct_all(page, enrichment_api, task_id)
    _open_detail(page, proposals[0]["id"])
    detail = page.get_by_test_id("enrichment-detail")
    detail.get_by_test_id("versions-toggle").click()
    expect(detail.get_by_test_id("version-2").get_by_test_id("version-instruction")).to_have_text(BATCH_INSTRUCTION)
    studio.shoot(page, "02-review-corrected", detail.get_by_test_id("version-2"))
    assert len(studio.task_calls(tracker_api, task_id, "enrichment.write.description")) == expected
    assert len(studio.task_calls(tracker_api, task_id, "enrichment.revise")) == expected


def _assert_compact(rows: Locator) -> None:
    """A Review row is one line: no inline preview stretches it."""
    for index in range(rows.count()):
        box = rows.nth(index).bounding_box()
        assert box and box["height"] <= COMPACT_ROW_MAX_PX, f"row {index} is {box and box['height']} px high"


def _open_detail(page: Page, proposal_id: int) -> None:
    page.get_by_test_id(f"enrichment-open-{proposal_id}").click()
    expect(page.get_by_test_id("enrichment-detail")).to_be_visible()


def _correct_all(page: Page, api: studio.AdminApi, task_id: int) -> None:
    """ "Correct all" with an instruction; the batch runs in the worker — wait until every proposal has version 2."""
    page.get_by_test_id("batch-correct").click()
    dialog = page.get_by_test_id("batch-correct-dialog")
    dialog.get_by_test_id("correction-instruction").locator("input").fill(BATCH_INSTRUCTION)
    dialog.get_by_test_id("correction-send").click()
    expect(dialog).to_be_hidden(timeout=pages.AI_TIMEOUT)
    ids = [proposal["id"] for proposal in studio.task_proposals(api, task_id)]
    corrected = studio.wait_for(lambda: all(len(studio.revisions(api, pk)) >= 2 for pk in ids), timeout=120)
    assert corrected, "the batch correction did not reach every proposal"
    page.reload()
