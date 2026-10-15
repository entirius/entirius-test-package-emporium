# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio in the CMS, run lanes: "Run now" (the express lane) and "Add to queue" (the bulk lane, one run at a time).

One product runs now from its drawer; a list selection is queued. To see a run wait, a blocker run over other
products is spawned through the API first and holds the bulk lane; repeating a run while it is still in flight
skips the products it already covers. Each test rejects what an earlier run left pending, so it re-runs on one seed.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from entirius_tests import ai_studio_e2e as studio
from entirius_tests import ai_studio_pages as pages
from entirius_tests.cms_e2e import CMS_BASE_URL, require_module

pytestmark = [require_module("enrichment"), pytest.mark.desktop_only]

NOW_SKU = "ENT-S003"
QUEUE_SKUS = ["ENT-D001", "ENT-D002", "ENT-D003"]
REPEAT_SKUS = ["ENT-O001", "ENT-O002", "ENT-O003"]
# Products no other AI studio test uses; a run over them keeps the bulk worker (concurrency 1) busy ~1 s each.
BLOCKER_SKUS = [
    "ENT-X001", "ENT-X002", "ENT-X003", "ENT-C004", "ENT-C005", "ENT-C006",
    "ENT-B004", "ENT-B005", "ENT-S006", "ENT-D004", "ENT-BND01", "ENT-BND02",
]  # fmt: skip
# Two runs over the blocker products: the lane stays busy for ~25 s.
BLOCKER_TEMPLATES = ["description", "meta"]


@pytest.fixture
def clean(enrichment_api: studio.AdminApi):
    """Nothing pending on the products of this file, before and after (the blocker's proposals included)."""
    skus = [NOW_SKU, *QUEUE_SKUS, *REPEAT_SKUS, *BLOCKER_SKUS]
    for sku in skus:
        studio.reject_pending(enrichment_api, sku)
    yield
    for sku in skus:
        studio.reject_pending(enrichment_api, sku)


def test_single_product_runs_now(admin_page: Page, enrichment_api: studio.AdminApi, clean: None):
    page = admin_page
    before = studio.latest_task_id(enrichment_api, NOW_SKU)
    page.goto(f"{CMS_BASE_URL}/pim/products/{NOW_SKU}")
    pages.open_drawer(page).get_by_role("button", name=pages.META_TEMPLATE, exact=True).click()
    dialog = page.get_by_test_id("ai-task-dialog")
    expect(dialog.get_by_test_id(pages.RUN_NOW)).to_have_class(re.compile("primary"))
    studio.shoot(page, "lanes-01-dialog-one-product", dialog)

    dialog.get_by_test_id(pages.RUN_NOW).click()
    expect(page.get_by_text("Running now")).to_be_visible()
    studio.shoot(page, "lanes-01-toast-running-now")
    task_id = studio.latest_task_id(enrichment_api, NOW_SKU)
    assert task_id > before
    assert studio.wait_task_finished(enrichment_api, task_id)["status"] == "done"
    assert studio.task(enrichment_api, task_id)["lane"] == "now"
    expect(pages.ai_trigger(page)).to_have_accessible_name(re.compile(r"\d+ to review"), timeout=pages.AI_TIMEOUT)


def test_selection_is_queued_then_done(admin_page: Page, enrichment_api: studio.AdminApi, clean: None):
    page = admin_page
    dialog = pages.open_bulk_dialog(page, QUEUE_SKUS, pages.DESCRIPTION_TEMPLATE)
    expect(dialog.get_by_test_id(pages.ADD_TO_QUEUE)).to_have_class(re.compile("primary"))
    studio.shoot(page, "lanes-02-dialog-selection", dialog)
    blockers = _hold_bulk_lane(enrichment_api)

    dialog.get_by_test_id(pages.ADD_TO_QUEUE).click()
    expect(page.get_by_text(re.compile(r"^Queued — "))).to_be_visible()
    studio.shoot(page, "lanes-02-toast-queued")
    dialog.get_by_test_id("ai-task-link").click()
    queued = page.get_by_test_id("enrichment-task-queued")
    expect(queued).to_be_visible()
    studio.shoot(page, "lanes-02-tasks-queued", queued)

    task_id = int(re.search(r"task=(\d+)", page.url).group(1))
    _wait_all(enrichment_api, [*blockers, task_id])
    expect(page.get_by_role("grid").get_by_text("Done", exact=True)).to_be_visible(timeout=15_000)
    assert len(studio.task_proposals(enrichment_api, task_id)) == len(QUEUE_SKUS) * len(studio.channel_languages())


def test_repeating_a_run_in_flight_skips_its_products(admin_page: Page, enrichment_api: studio.AdminApi, clean: None):
    page = admin_page
    blockers = _hold_bulk_lane(enrichment_api)
    first = pages.open_bulk_dialog(page, REPEAT_SKUS[:2], pages.DESCRIPTION_TEMPLATE)
    first.get_by_test_id(pages.ADD_TO_QUEUE).click()
    expect(first.get_by_test_id("ai-task-created")).to_be_visible()

    partial = pages.open_bulk_dialog(page, REPEAT_SKUS, pages.DESCRIPTION_TEMPLATE)
    partial.get_by_test_id(pages.ADD_TO_QUEUE).click()
    expect(page.get_by_text("2 products skipped, already running.")).to_be_visible()
    studio.shoot(page, "lanes-03-toast-skipped")

    again = pages.open_bulk_dialog(page, REPEAT_SKUS, pages.DESCRIPTION_TEMPLATE)
    again.get_by_test_id(pages.ADD_TO_QUEUE).click()
    expect(page.get_by_text("This run is already in progress for all 3 items. Wait for it to finish.")).to_be_visible()
    expect(again).to_be_hidden()
    studio.shoot(page, "lanes-03-toast-already-running")
    _wait_all(enrichment_api, [*blockers, *_tasks_of(enrichment_api, REPEAT_SKUS)])


def _hold_bulk_lane(api: studio.AdminApi) -> list[int]:
    """Queued runs over the blocker products; returns their ids. The first one starts at once if the lane is idle."""
    return [_spawn_blocker(api, template)["id"] for template in BLOCKER_TEMPLATES]


def _spawn_blocker(api: studio.AdminApi, template: str) -> dict:
    scope = {"mode": "list", "module": "pim", "channel": studio.CHANNEL, "refs": BLOCKER_SKUS}
    body = {"type": "pim.writer", "template": template, "lane": "queue", "params": {"channel": studio.CHANNEL}}
    return api.post(f"{studio.ENRICHMENT}/tasks/", {**body, "scope_spec": scope})


def _tasks_of(api: studio.AdminApi, skus: list[str]) -> set[int]:
    return {studio.latest_task_id(api, sku) for sku in skus}


def _wait_all(api: studio.AdminApi, task_ids: list[int] | set[int]) -> None:
    for task_id in task_ids:
        studio.wait_task_finished(api, task_id, timeout=180)
