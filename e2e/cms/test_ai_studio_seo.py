# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio in the CMS, scenario 3: SEO research before writing, shared by the products of one category.

The writer runs with "SEO research" on two products of one category: the first product researches (one SEO
brief per language, remembered under the category), the second reuses it — so every research call of the task is
made once per language, not once per product. Memory shows the brief with its expiry.
Skipped while the AI toolbox has no SEO app (`/api/ai-seo/`): the local image gets it only after a rebuild.
"""

from __future__ import annotations

from collections import Counter

import pytest
from playwright.sync_api import Page, expect

from entirius_tests import ai_studio_e2e as studio
from entirius_tests import ai_studio_pages as pages
from entirius_tests.cms_e2e import CMS_BASE_URL, require_module

pytestmark = [require_module("enrichment"), pytest.mark.desktop_only, pytest.mark.usefixtures("require_toolbox_seo")]

SKUS = ["ENT-B002", "ENT-B003"]  # one category in the Emporium catalogue
RESEARCH_SELECTOR = "enrichment.seo_brief"


@pytest.fixture
def fresh_research(enrichment_api: studio.AdminApi) -> list[str]:
    """Nothing pending on the products and no remembered product SEO brief, so the run has to research."""
    for sku in SKUS:
        studio.reject_pending(enrichment_api, sku)
    briefs = enrichment_api.get(f"{studio.ENRICHMENT}/memory/", kind="seo_brief", page_size=200)["results"]
    for brief in briefs:
        if brief["subject_module"] == "pim":
            enrichment_api.call("DELETE", f"{studio.ENRICHMENT}/memory/{brief['id']}/")
    return SKUS


def test_seo_research_runs_once_per_category(
    admin_page: Page, enrichment_api: studio.AdminApi, tracker_api: studio.AdminApi, fresh_research: list[str]
):
    page = admin_page
    languages = studio.channel_languages()
    task_id = pages.bulk_run(page, fresh_research, pages.META_TEMPLATE, research=True)
    finished = studio.wait_task_finished(enrichment_api, task_id, timeout=180)
    assert finished["status"] == "done", finished["errors"]

    research = Counter(_selector(r) for r in studio.task_calls(tracker_api, task_id, RESEARCH_SELECTOR))
    assert research, "the task made no SEO research call"
    assert set(research.values()) == {len(languages)}, research  # once per language, not per product
    writes = studio.task_calls(tracker_api, task_id, "enrichment.write.meta")
    assert len(writes) == len(fresh_research) * len(languages)

    brief = enrichment_api.get(f"{studio.ENRICHMENT}/memory/", kind="seo_brief", page_size=1)["results"][0]
    page.goto(f"{CMS_BASE_URL}/enrichment/memory")
    entry = page.get_by_test_id(f"memory-entry-{brief['id']}")
    expect(entry.get_by_test_id("memory-brief-primary")).to_be_visible()
    expect(entry.get_by_test_id("memory-brief-expiry")).to_be_visible()
    studio.shoot(page, "03-seo-brief", entry)


def _selector(record: dict) -> str:
    return record["metadata"]["tags"][0]
