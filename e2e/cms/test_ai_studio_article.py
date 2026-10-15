# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio in the CMS, scenario 6: an article written step by step in Studio.

New → brief → questions (answered, approved) → search phrases (primary picked) → outline (one AI correction) →
draft → metadata (search preview) → document → "Open draft in Pages": the draft exists and is not published;
the run cost is shown. Every run is new (its own brief), so the test re-runs on one seed.
The search-phrases step researches through the toolbox SEO app: without it (`/api/ai-seo/`, the local image before
its rebuild) that step fails, so the test stops there with a skip after checking the questions part.
The fake models mark every question optional, so the required-answer check runs only when a question is required;
otherwise the test warns that it was not exercised.
"""

from __future__ import annotations

import re
import warnings

import pytest
from playwright.sync_api import Locator, Page, expect

from entirius_tests import ai_studio_e2e as studio
from entirius_tests import ai_studio_pages as pages
from entirius_tests.cms_e2e import require_module

pytestmark = [require_module("enrichment"), pytest.mark.desktop_only]

TOPIC = "BDD e2e: stowing a sofa before a hard burn"
ANSWER = "Every sofa locks to the floor rail."
OUTLINE_INSTRUCTION = "Add a section on spare parts."
CONTENT_ADMIN = "api-admin/contentdb/v1/content/blog-post"


def step_panel(page: Page, key: str) -> Locator:
    """The panel of a step once it waits for review (its output and the approve primary, named by its next step)."""
    page.get_by_test_id(f"step-{key}").click()
    panel = page.get_by_test_id(f"step-panel-{key}")
    expect(panel.get_by_test_id("step-approve")).to_be_visible(timeout=pages.AI_TIMEOUT)
    return panel


def approve(panel: Locator) -> None:
    panel.get_by_test_id("step-approve").click()
    expect(panel.get_by_test_id("step-approve")).to_have_count(0, timeout=pages.AI_TIMEOUT)


@pytest.fixture
def started_runs(enrichment_api: studio.AdminApi):
    """Runs the test starts; one left open (a failed or skipped test) is cancelled afterwards."""
    uids: list[str] = []
    yield uids
    for uid in uids:
        if enrichment_api.get(f"{studio.ENRICHMENT}/runs/{uid}/")["status"] not in ("done", "cancelled"):
            enrichment_api.post(f"{studio.ENRICHMENT}/runs/{uid}/cancel/")


def test_article_run_end_to_end(
    admin_page: Page, enrichment_api: studio.AdminApi, started_runs: list[str], toolbox_seo: bool
):
    page = admin_page
    uid = _start_run(page)
    started_runs.append(uid)
    _answer_questions(page, enrichment_api, uid)
    if not toolbox_seo:
        expect(page.get_by_test_id("step-panel-keywords").get_by_test_id("step-failed")).to_be_visible(
            timeout=pages.AI_TIMEOUT
        )
        pytest.skip("the search-phrases step needs the AI toolbox SEO app (/api/ai-seo/), not served yet")

    _pick_keywords(page)
    _correct_outline(page)
    approve(step_panel(page, "draft"))
    meta = step_panel(page, "meta")
    expect(meta.get_by_test_id("meta-cards").get_by_test_id("search-snippet")).to_be_visible()
    studio.shoot(page, "06-article-meta", meta)
    approve(meta)
    _open_draft(page, enrichment_api, uid)


def _start_run(page: Page) -> str:
    dialog = pages.open_guided(page, "Article")
    dialog.get_by_role("textbox", name="Topic").fill(TOPIC)
    studio.shoot(page, "06-article-brief", dialog)
    dialog.get_by_role("button", name="Start").click()
    page.wait_for_url(re.compile(r"/enrichment/studio/[0-9a-f]+"))
    return page.url.split("?")[0].rsplit("/", 1)[-1]


def _answer_questions(page: Page, api: studio.AdminApi, uid: str) -> None:
    """Required answers are enforced on Approve; every question gets an answer, saved when the field is left."""
    panel = step_panel(page, "questions")
    questions = _questions(api, uid)
    if any(not question.get("optional") for question in questions):
        panel.get_by_test_id("step-approve").click()
        expect(panel.get_by_text("An answer is required").first).to_be_visible()
    else:
        warnings.warn("required-answer check not exercised: the model marked every question optional", stacklevel=2)
    for index, question in enumerate(questions):
        _answer(panel.get_by_test_id(f"question-{index}"), question)
    panel.get_by_role("heading", name="Questions").click()  # leaving the field saves the answers
    expect(panel.get_by_test_id("answers-saved")).to_be_visible()
    expect(panel.get_by_test_id("answers-dirty")).to_be_hidden()
    studio.shoot(page, "06-article-questions", panel)
    approve(panel)


def _questions(api: studio.AdminApi, uid: str) -> list[dict]:
    run = api.get(f"{studio.ENRICHMENT}/runs/{uid}/")
    proposal_id = next(step["proposal_id"] for step in run["steps"] if step["key"] == "questions")
    return api.get(f"{studio.ENRICHMENT}/proposals/{proposal_id}/")["proposed_value"]["questions"]


def _answer(field: Locator, question: dict) -> None:
    """Free text, or the first choice (radio buttons, a dropdown for long lists)."""
    if not question.get("choices"):
        field.get_by_role("textbox").fill(ANSWER)
    elif field.get_by_role("radio").count():
        field.get_by_role("radio").first.check()
    else:
        field.get_by_role("combobox").click()
        field.page.get_by_role("option").first.click()


def _pick_keywords(page: Page) -> None:
    panel = step_panel(page, "keywords")
    table = panel.get_by_test_id("keywords-table")
    table.get_by_test_id(re.compile(r"^keyword-row-")).first.get_by_test_id("keyword-primary").click()
    expect(table.get_by_test_id("keywords-primary")).not_to_have_text("—")
    studio.shoot(page, "06-article-keywords", table)
    approve(panel)


def _correct_outline(page: Page) -> None:
    panel = step_panel(page, "outline")
    panel.get_by_test_id("correction-toggle").click()
    panel.get_by_test_id("correction-instruction").locator("textarea").fill(OUTLINE_INSTRUCTION)
    panel.get_by_test_id("correction-send").click()
    expect(panel.get_by_test_id("correction-busy")).to_be_hidden(timeout=pages.AI_TIMEOUT)
    expect(panel.get_by_test_id("thread-ask-2").get_by_test_id("ask-text")).to_have_text(OUTLINE_INSTRUCTION)
    studio.shoot(page, "06-article-outline", panel)
    approve(panel)


def _open_draft(page: Page, api: studio.AdminApi, uid: str) -> None:
    """Approving the document creates the ContentDB draft — not published — and the run shows what it cost."""
    approve(step_panel(page, "compose"))
    expect(page.get_by_test_id("run-cost")).to_contain_text("$")
    link = page.get_by_test_id("open-draft")
    expect(link).to_be_visible()
    studio.shoot(page, "06-article-document", page.get_by_test_id("step-panel-compose"))
    draft = api.get(f"{studio.ENRICHMENT}/runs/{uid}/")["subject_ref"]
    assert draft, "the finished run names no draft"
    link.click()
    expect(page).to_have_url(re.compile(re.escape(draft)))
    assert api.get(f"{CONTENT_ADMIN}/{draft}/")["data"], "the draft is missing in ContentDB"
    assert api.get(f"{CONTENT_ADMIN}/{draft}/published/")["pagination"]["records"] == 0, "the draft is published"
