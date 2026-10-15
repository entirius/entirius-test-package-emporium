# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio in the CMS, scenario 5: AI templates — create, reorder, deactivate; the product drawer follows.

The test template is created in the CMS and removed by API before and after (key prefix `bdd-`), so the test
re-runs on one seed and leaves the seeded templates as they were.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Locator, Page, expect

from entirius_tests import ai_studio_e2e as studio
from entirius_tests import ai_studio_pages as pages
from entirius_tests.cms_e2e import CMS_BASE_URL, require_module

pytestmark = [require_module("enrichment"), pytest.mark.desktop_only]

LABEL = "BDD e2e template"
KEY_PREFIX = "bdd-e2e-template"
DRAWER_SKU = "ENT-S004"
LAST_SEEDED = "Otaguj produkt"  # the last seeded product template (service fixtures)


@pytest.fixture
def clean_templates(enrichment_api: studio.AdminApi):
    studio.delete_templates(enrichment_api, KEY_PREFIX)
    seeded = {t["key"]: t["position"] for t in enrichment_api.get(f"{studio.ENRICHMENT}/templates/")}
    yield
    studio.delete_templates(enrichment_api, KEY_PREFIX)
    for key, position in seeded.items():  # a reorder renumbers its neighbours too
        enrichment_api.call("PATCH", f"{studio.ENRICHMENT}/templates/{key}/", json={"position": position})


def table_labels(page: Page) -> list[str]:
    rows = page.get_by_test_id("templates-table").get_by_role("row")
    return [cell.strip() for cell in rows.locator("[role=gridcell]:first-child").all_inner_texts()]


def _above(labels: list[str], first: str, second: str) -> bool:
    texts = [text.strip() for text in labels]
    return first in texts and second in texts and texts.index(first) < texts.index(second)


def drawer_templates(page: Page) -> Locator:
    page.goto(f"{CMS_BASE_URL}/pim/products/{DRAWER_SKU}")
    return pages.open_drawer(page).get_by_role("region", name="Run AI").get_by_role("button")


def test_templates_create_reorder_deactivate(admin_page: Page, enrichment_api: studio.AdminApi, clean_templates):
    page = admin_page
    _create_template(page)
    expect(page.get_by_test_id("templates-table")).to_contain_text(LABEL)
    assert table_labels(page)[-1] == LABEL
    studio.shoot(page, "05-templates-list")

    key = next(t["key"] for t in enrichment_api.get(f"{studio.ENRICHMENT}/templates/") if t["label"] == LABEL)
    page.get_by_test_id(f"template-up-{key}").click()
    moved = studio.wait_for(lambda: _above(table_labels(page), LABEL, LAST_SEEDED), timeout=10, every=0.3)
    assert moved, table_labels(page)
    offered = drawer_templates(page)
    expect(offered.filter(has_text=LABEL)).to_be_visible()
    assert _above(offered.all_inner_texts(), LABEL, LAST_SEEDED), offered.all_inner_texts()
    studio.shoot(page, "05-templates-drawer", page.get_by_test_id("ai-results-drawer"))

    _deactivate(page, key)
    expect(drawer_templates(page).filter(has_text=LAST_SEEDED)).to_be_visible()
    expect(drawer_templates(page).filter(has_text=LABEL)).to_have_count(0)


def _create_template(page: Page) -> None:
    page.goto(f"{CMS_BASE_URL}/enrichment/settings/templates")
    page.get_by_role("button", name="Toggle menu").click()
    page.get_by_role("menuitem", name="New template").click()
    page.get_by_test_id("template-label").locator("input").fill(LABEL)
    page.get_by_test_id("template-worker").click()
    page.get_by_role("option", name="Product writer", exact=True).click()
    page.get_by_role("combobox", name="Fields").click()
    page.get_by_role("option", name="Meta title", exact=True).click()
    page.keyboard.press("Escape")
    page.get_by_test_id("template-save").click()
    expect(page).to_have_url(re.compile(r"/enrichment/settings/templates$"))


def _deactivate(page: Page, key: str) -> None:
    page.goto(f"{CMS_BASE_URL}/enrichment/settings/templates/{key}")
    page.get_by_test_id("template-active").get_by_role("switch").click()
    page.get_by_test_id("template-save").click()
    expect(page).to_have_url(re.compile(r"/enrichment/settings/templates$"))
    row = page.get_by_test_id("templates-table").get_by_role("row").filter(has_text=LABEL)
    expect(row).not_to_contain_text("Offered")
    studio.shoot(page, "05-templates-deactivated", row)
