# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio in the CMS, scenario 4: company profile and QA warnings.

The profile gets a fact and the rule "e-commerce → ecommerce" (version +1). The fake models never write
"e-commerce" or a number, so the operator's manual edit of a writer proposal brings them in — a manual edit is a
version and is checked like an AI one. The card shows both warnings; "Add to facts" leaves a suggestion in Memory,
"Fix warnings" makes a version without the rule warning. The suggestion belongs to the product's channel, so
promoting it adds a version to that channel's overlay (not to the whole-company profile). The fixture saves the
company profile and the overlay from before the test back as new versions.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Locator, Page, expect

from entirius_tests import ai_studio_e2e as studio
from entirius_tests import ai_studio_pages as pages
from entirius_tests.cms_e2e import CMS_BASE_URL, require_module

pytestmark = [require_module("enrichment"), pytest.mark.desktop_only]

SKU = "ENT-S002"
FACT = {"What *": "E2E dock clamp rating", "Value *": "12 kN"}
RULE = {
    "Pattern *": "e-commerce",
    "Message *": "Write ecommerce as one word.",
    "DO": "ecommerce",
    "DON'T": "e-commerce",
}
UNKNOWN_NUMBER = "4321"
EDITED_TEXT = f"The e-commerce favourite: docks in {UNKNOWN_NUMBER} cycles without a scratch."
NOTE = "e2e: dock clamp fact, ecommerce spelling rule"
RESTORED = "e2e: restored after the QA test"


@pytest.fixture
def profile_version(enrichment_api: studio.AdminApi):
    """The company profile version before the test; its data and the channel overlay are saved back afterwards."""
    studio.reject_pending(enrichment_api, SKU)
    before = studio.profile(enrichment_api)
    overlay = studio.profile(enrichment_api, studio.CHANNEL)["data"]
    yield before["version"]
    studio.put_profile(enrichment_api, before["data"], RESTORED)
    studio.put_profile(enrichment_api, overlay, RESTORED, studio.CHANNEL)


def test_profile_rule_and_qa_warnings(
    admin_page: Page, enrichment_api: studio.AdminApi, tracker_api: studio.AdminApi, profile_version: int
):
    page = admin_page
    _edit_profile(page)
    assert studio.wait_for(lambda: studio.profile(enrichment_api)["version"] == profile_version + 1, timeout=10)
    page.get_by_test_id("profile-history-open").click()
    expect(page.get_by_test_id(f"profile-version-{profile_version + 1}")).to_contain_text(NOTE)
    studio.shoot(page, "04-profile-history", page.get_by_test_id("profile-history"))

    card = _edited_card(page, enrichment_api)
    expect(card.get_by_test_id("qa-warning-rule")).to_be_visible()
    number = card.get_by_test_id("qa-warning-NUMBER_NOT_IN_FACTS")
    expect(number).to_contain_text(UNKNOWN_NUMBER)
    studio.shoot(page, "04-qa-warnings", card)

    number.get_by_test_id("qa-add-fact").click()
    expect(number.get_by_test_id("qa-add-fact")).to_be_disabled()
    card.get_by_test_id("qa-fix-warnings").click()
    expect(card.get_by_test_id("qa-warning-rule")).to_have_count(0, timeout=pages.AI_TIMEOUT)
    assert len(studio.task_calls(tracker_api, studio.latest_task_id(enrichment_api, SKU), "enrichment.revise")) == 1

    overlay = studio.profile(enrichment_api, studio.CHANNEL)["version"]
    _promote_suggestion(page, enrichment_api)
    promoted = studio.wait_for(lambda: _overlay_fact(enrichment_api, overlay + 1), timeout=10)
    assert promoted, "the promoted fact did not reach the channel profile"


def _overlay_fact(api: studio.AdminApi, version: int) -> bool:
    found = studio.profile(api, studio.CHANNEL)
    values = [fact.get("value") for fact in found["data"].get("facts", [])]
    return found["version"] == version and UNKNOWN_NUMBER in values


def _fill_last_row(page: Page, table: str, values: dict[str, str]) -> None:
    """Add a row to a profile table and fill it (labels of the row's inputs)."""
    rows = page.locator(f"[data-testid^='{table}-row-']")
    count = rows.count()
    page.get_by_test_id(f"{table}-add").click()
    row = page.get_by_test_id(f"{table}-row-{count}")
    for label, value in values.items():
        row.get_by_role("textbox", name=label, exact=True).fill(value)


def _edit_profile(page: Page) -> None:
    page.goto(f"{CMS_BASE_URL}/enrichment/settings/profile")
    expect(page.get_by_test_id("profile-facts-row-0")).to_be_visible()
    _fill_last_row(page, "profile-facts", FACT)
    _fill_last_row(page, "profile-rules", RULE)
    page.get_by_test_id("profile-note").locator("input").fill(NOTE)
    page.get_by_test_id("profile-save").click()
    expect(page.get_by_test_id("profile-unsaved")).to_be_hidden()


def _edited_card(page: Page, api: studio.AdminApi) -> Locator:
    """Run the writer on the product, then edit its EN meta description by hand to bring in the rule and a number."""
    before = studio.latest_task_id(api, SKU)
    page.goto(f"{CMS_BASE_URL}/pim/products/{SKU}")
    pages.run_template(page, pages.open_drawer(page), pages.META_TEMPLATE)
    expect(page.get_by_text("AI task finished")).to_be_visible(timeout=pages.AI_TIMEOUT)
    assert studio.latest_task_id(api, SKU) > before
    card = pages.proposal_card(page, pages.open_drawer(page), "Meta description", "EN")
    card.get_by_test_id("proposal-edit").click()
    card.get_by_test_id("proposal-edit-text").locator("textarea").fill(EDITED_TEXT)
    card.get_by_test_id("proposal-save").click()
    return card


def _promote_suggestion(page: Page, api: studio.AdminApi) -> None:
    """Memory: the fact suggestion "Add to facts" left → Add to profile."""
    query = {"kind": "fact_suggestion", "status": "active", "page_size": 50}
    entries = api.get(f"{studio.ENRICHMENT}/memory/", **query)["results"]
    suggestion = max((e for e in entries if UNKNOWN_NUMBER in f"{e['title']} {e['text']}"), key=lambda e: e["id"])
    page.goto(f"{CMS_BASE_URL}/enrichment/settings/memory")
    entry = page.get_by_test_id(f"memory-entry-{suggestion['id']}")
    expect(entry).to_be_visible()
    studio.shoot(page, "04-memory-suggestion", entry)
    entry.get_by_test_id("memory-promote").click()
    expect(entry.get_by_test_id("memory-promote")).to_have_count(0)
