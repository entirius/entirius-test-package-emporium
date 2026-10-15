# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio in the CMS, scenario 9: pictures and video through the fake toolbox media app.

A video made from a picture chosen in the run dialog; a packshot of a product picture applied next to the original
and undone; a packshot of a gallery image added to the gallery (tagged `ai`) and undone. Every test rejects what is
left to review and reverts what it applied, before and after, so it re-runs on one seed.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import Locator, Page, expect

from entirius_tests import ai_studio_e2e as studio
from entirius_tests import ai_studio_pages as pages
from entirius_tests.cms_e2e import CMS_BASE_URL, require_module

pytestmark = [require_module("enrichment"), pytest.mark.desktop_only]

VIDEO_SKU = "ENT-C006"
PACKSHOT_SKU = "ENT-C005"
VIDEO_WORKER = "Social video from main picture"
PACKSHOT_TEMPLATE = "Packshot na białym tle"
GALLERY_PACKSHOT_TEMPLATE = "Galeria: packshot na białym tle"
AI_TAG = "ai"


@pytest.fixture
def clean_video(enrichment_api: studio.AdminApi) -> Iterator[str]:
    studio.reject_pending(enrichment_api, VIDEO_SKU)
    yield VIDEO_SKU
    studio.reject_pending(enrichment_api, VIDEO_SKU)


@pytest.fixture
def clean_packshot(enrichment_api: studio.AdminApi) -> Iterator[str]:
    _reset_product(enrichment_api)
    yield PACKSHOT_SKU
    _reset_product(enrichment_api)


def _reset_product(api: studio.AdminApi) -> None:
    studio.reject_pending(api, PACKSHOT_SKU)
    studio.undo_applied_pictures(api, "pim", PACKSHOT_SKU)


@pytest.fixture
def gallery_source(enrichment_api: studio.AdminApi) -> Iterator[str]:
    """A seeded gallery image (not made by AI); images a failed earlier run left behind are removed after."""
    before = {image["uid"] for image in studio.gallery_images(enrichment_api)}
    uid = next(image["uid"] for image in studio.gallery_images(enrichment_api) if not _tagged_ai(image))
    _reset_gallery(enrichment_api, uid)
    yield uid
    _reset_gallery(enrichment_api, uid)
    for image in studio.gallery_images(enrichment_api):
        if image["uid"] not in before:
            studio.delete_gallery_image(enrichment_api, image["uid"])


def _reset_gallery(api: studio.AdminApi, uid: str) -> None:
    for proposal in api.get(f"{studio.ENRICHMENT}/proposals/", search=uid, status="pending", page_size=50)["results"]:
        api.post(f"{studio.ENRICHMENT}/proposals/{proposal['id']}/reject/", {"reason": "e2e reset"})
    studio.undo_applied_pictures(api, "contentdb", uid)


def _tagged_ai(image: dict) -> bool:
    return any(tag.get("slug") == AI_TAG for tag in image.get("tags") or [])


def test_video_from_a_chosen_picture(admin_page: Page, enrichment_api: studio.AdminApi, clean_video: str):
    page = admin_page
    offered = studio.pictures(enrichment_api, clean_video)
    chosen = offered[-1]["ref"]
    before = studio.latest_task_id(enrichment_api, clean_video)
    page.goto(f"{CMS_BASE_URL}/pim/products/{clean_video}")
    pages.open_drawer(page).get_by_test_id("ai-run-custom").click()
    dialog = page.get_by_test_id("ai-task-dialog")
    dialog.get_by_test_id("ai-task-worker").click()
    page.get_by_role("option", name=VIDEO_WORKER, exact=True).click()

    picker = dialog.get_by_test_id("picture-picker")
    expect(picker.get_by_role("radio")).to_have_count(len(offered))
    _pick_picture(dialog, chosen)
    studio.shoot(page, "09-video-picker", dialog)
    dialog.get_by_test_id(pages.RUN_NOW).click()

    task_id = studio.wait_for(lambda: _newer_task(enrichment_api, clean_video, before), timeout=30)
    assert task_id, "no video task was created"
    assert studio.wait_task_finished(enrichment_api, task_id, timeout=180)["status"] == "done"
    assert studio.task(enrichment_api, task_id)["params"]["picture_ref"] == chosen
    videos = [p for p in studio.task_proposals(enrichment_api, task_id) if p["target_kind"] == "video"]
    assert len(videos) == 1, studio.task_proposals(enrichment_api, task_id)
    card = pages.open_drawer(page).get_by_test_id(f"proposal-panel-{videos[0]['id']}")
    expect(card.locator("video")).to_be_visible(timeout=pages.AI_TIMEOUT)
    studio.shoot(page, "09-video-proposal", card)


def test_product_packshot_added_then_undone(admin_page: Page, enrichment_api: studio.AdminApi, clean_packshot: str):
    page = admin_page
    count = len(studio.pictures(enrichment_api, clean_packshot))
    before = studio.latest_task_id(enrichment_api, clean_packshot)
    page.goto(f"{CMS_BASE_URL}/pim/products/{clean_packshot}")
    pages.open_drawer(page).get_by_role("button", name=PACKSHOT_TEMPLATE, exact=True).click()
    dialog = page.get_by_test_id("ai-task-dialog")
    expect(dialog.get_by_test_id("picture-picker").get_by_role("radio", checked=True)).to_have_count(1)
    dialog.get_by_test_id(pages.RUN_NOW).click()

    task_id = studio.wait_for(lambda: _newer_task(enrichment_api, clean_packshot, before), timeout=30)
    assert task_id, "no packshot task was created"
    proposal = _only_picture(enrichment_api, task_id)
    card = pages.open_drawer(page).get_by_test_id(f"proposal-panel-{proposal['id']}")
    expect(card.get_by_test_id("image-diff-after-img")).to_be_visible(timeout=pages.AI_TIMEOUT)
    studio.shoot(page, "09-packshot-proposal", card)
    _apply_added(page, card)
    assert studio.wait_for(lambda: len(studio.pictures(enrichment_api, clean_packshot)) == count + 1, timeout=15)

    _undo_pictures(page, clean_packshot)
    assert studio.wait_for(lambda: len(studio.pictures(enrichment_api, clean_packshot)) == count, timeout=15)


def test_gallery_packshot_added_then_undone(admin_page: Page, enrichment_api: studio.AdminApi, gallery_source: str):
    page = admin_page
    before = {image["uid"] for image in studio.gallery_images(enrichment_api)}
    page.goto(f"{CMS_BASE_URL}/pages/gallery")
    select = page.get_by_test_id(f"gallery-select-{gallery_source}")
    select.locator("xpath=ancestor::*[@role='group'][1]").hover()  # a tile shows its actions on hover
    select.check()
    expect(page.get_by_test_id("gallery-bulk-bar")).to_be_visible()
    page.get_by_role("combobox", name="AI: process images").click()
    page.get_by_role("option", name=GALLERY_PACKSHOT_TEMPLATE, exact=True).click()
    dialog = page.get_by_test_id("ai-task-dialog")
    studio.shoot(page, "09-gallery-dialog", dialog)
    dialog.get_by_test_id(pages.RUN_NOW).click()
    link = dialog.get_by_test_id("ai-task-link")
    expect(link).to_have_attribute("href", re.compile(r"task=\d+"))
    task_id = int(re.search(r"task=(\d+)", link.get_attribute("href") or "").group(1))

    proposal = _only_picture(enrichment_api, task_id)
    page.goto(f"{CMS_BASE_URL}/enrichment?task={task_id}")
    page.get_by_test_id(f"enrichment-open-{proposal['id']}").click()
    detail = page.get_by_test_id("enrichment-detail")
    expect(detail.get_by_test_id("image-diff-after-img")).to_be_visible()
    _apply_added(page, detail)
    added = studio.wait_for(lambda: _new_images(enrichment_api, before), timeout=15)
    assert len(added) == 1 and _tagged_ai(added[0]), added

    page.goto(f"{CMS_BASE_URL}/pages/gallery")
    expect(page.get_by_test_id(f"gallery-select-{added[0]['uid']}")).to_be_attached()
    studio.shoot(page, "09-gallery-added")
    _undo_pictures(page, gallery_source)
    assert studio.wait_for(lambda: not _new_images(enrichment_api, before), timeout=15)


def _pick_picture(dialog: Locator, ref: str) -> None:
    """A picture tile hides its radio: the tile (its label) is what the operator clicks."""
    radio = dialog.get_by_test_id(f"picture-picker-item-{ref}")
    radio.locator("xpath=ancestor::label[1]").click()
    expect(radio).to_be_checked()


def _newer_task(api: studio.AdminApi, sku: str, before: int) -> int:
    latest = studio.latest_task_id(api, sku)
    return latest if latest > before else 0


def _only_picture(api: studio.AdminApi, task_id: int) -> dict:
    assert studio.wait_task_finished(api, task_id, timeout=120)["status"] == "done", studio.task(api, task_id)
    found = [p for p in studio.task_proposals(api, task_id) if p["target_kind"] == "picture"]
    assert len(found) == 1, studio.task_proposals(api, task_id)
    return found[0]


def _apply_added(page: Page, card: Locator) -> None:
    """Apply with "Add next to the original" (the default, picked explicitly)."""
    mode = card.get_by_test_id("proposal-apply-mode")
    mode.get_by_text("Add next to the original").click()
    expect(mode.get_by_test_id("proposal-apply-mode-add")).to_be_checked()
    card.get_by_test_id("proposal-accept").click()
    expect(page.get_by_text("Proposal accepted.")).to_be_visible()


def _undo_pictures(page: Page, search: str) -> None:
    """Review → Applied → the subject's picture proposals → "Undo all"."""
    page.goto(f"{CMS_BASE_URL}/enrichment?status=applied")
    page.get_by_role("textbox", name="Search by name or SKU…").fill(search)
    expect(page.get_by_test_id("enrichment-count")).to_contain_text(re.compile(r"\d"))
    page.get_by_test_id("enrichment-kind-filter").click()
    page.get_by_role("option", name="picture", exact=True).click()
    expect(page.get_by_test_id("enrichment-undo")).to_have_text(re.compile(r"\(1\)"))
    page.get_by_test_id("enrichment-undo").click()
    page.get_by_test_id("enrichment-bulk-confirm").click()
    expect(page.get_by_text("1 proposals reverted.")).to_be_visible()


def _new_images(api: studio.AdminApi, before: set[str]) -> list[dict]:
    return [image for image in studio.gallery_images(api) if image["uid"] not in before]
