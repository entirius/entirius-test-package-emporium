# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio in the CMS, scenario 7: errors in plain words.

A toolbox 400: the fake toolbox has no error switch, so a test template asks for a JSON answer whose schema is not
a valid JSON Schema — the toolbox rejects the request (400 VALIDATION_ERROR) and the task fails. Template and task
are made by API (the template belongs to a workflow-step worker, which the CMS runs only inside a run); the CMS
shows the failed task in the product's AI drawer.

The profile soft gate: every channel inherits the whole-company profile, so an incomplete profile is simulated by
saving an empty one; the fixture saves the previous data back as a new version.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from entirius_tests import ai_studio_e2e as studio
from entirius_tests import ai_studio_pages as pages
from entirius_tests.cms_e2e import CMS_BASE_URL, require_module

pytestmark = [require_module("enrichment"), pytest.mark.desktop_only]

FAILING_SKU = "ENT-S005"
BROKEN_KEY = "bdd-e2e-broken-schema"
BROKEN_TEMPLATE = {
    "key": BROKEN_KEY,
    "label": "BDD e2e broken schema",
    "worker_key": "article.outline",
    "params": {"format": "json", "json_schema": {"type": "object", "properties": {"x": {"type": "no-such-type"}}}},
    "rules": [],
    "position": 990,
    "active": True,
}


@pytest.fixture
def broken_template(enrichment_api: studio.AdminApi):
    studio.delete_templates(enrichment_api, BROKEN_KEY)
    enrichment_api.post(f"{studio.ENRICHMENT}/templates/", BROKEN_TEMPLATE)
    yield BROKEN_KEY
    studio.delete_templates(enrichment_api, BROKEN_KEY)


def spawn_on_product(api: studio.AdminApi, template: str, sku: str) -> int:
    scope = {"mode": "list", "refs": [sku], "module": "pim", "channel": studio.CHANNEL}
    body = {"template": template, "scope_spec": scope, "params": {"channel": studio.CHANNEL}}
    return api.post(f"{studio.ENRICHMENT}/tasks/", body)["id"]


ERROR_CODE = re.compile(r"[A-Z]{3,}_[A-Z_]+")


def test_toolbox_rejection_is_a_plain_failed_row(
    admin_page: Page, enrichment_api: studio.AdminApi, tracker_api: studio.AdminApi, broken_template: str
):
    task_id = spawn_on_product(enrichment_api, broken_template, FAILING_SKU)
    finished = studio.wait_task_finished(enrichment_api, task_id)
    assert finished["status"] == "failed"
    assert [error["code"] for error in finished["errors"]] == ["VALIDATION_ERROR"]
    assert studio.task_calls(tracker_api, task_id) == []  # a rejected request is not billed

    admin_page.goto(f"{CMS_BASE_URL}/pim/products/{FAILING_SKU}")
    pages.open_drawer(admin_page)
    row = admin_page.get_by_test_id(f"ai-task-{task_id}")
    outcome = row.get_by_test_id("ai-task-outcome")
    studio.shoot(admin_page, "07-failed-task", row)
    expect(row).to_contain_text(BROKEN_TEMPLATE["label"])
    expect(outcome).to_have_text(re.compile(r"^Failed: \S.+"))
    expect(outcome).not_to_contain_text(ERROR_CODE)  # no toolbox error codes
    expect(row).not_to_contain_text(BROKEN_TEMPLATE["worker_key"])  # no workers on the surface


@pytest.fixture
def empty_profile(enrichment_api: studio.AdminApi):
    saved = studio.profile(enrichment_api)["data"]
    studio.put_profile(enrichment_api, {}, "e2e: empty profile (soft gate)")
    yield
    studio.put_profile(enrichment_api, saved, "e2e: profile restored after the soft gate test")


def test_incomplete_profile_soft_gate(admin_page: Page, empty_profile):
    page = admin_page
    page.goto(f"{CMS_BASE_URL}/enrichment/studio")
    page.get_by_role("button", name="New").click()
    gate = page.get_by_test_id("new-run-dialog").get_by_test_id("profile-gate")
    expect(gate).to_be_visible()
    expect(gate).to_contain_text("Facts")
    studio.shoot(page, "07-profile-gate", gate)
    page.keyboard.press("Escape")

    page.get_by_test_id("config-health-button").click()
    panel = page.get_by_test_id("config-health-panel")
    recheck = panel.get_by_test_id("config-health-recheck")
    if recheck.count():
        recheck.click()
    row = panel.get_by_test_id("config-health-row").filter(has_text="Company profile")
    expect(row).to_contain_text("incomplete")
    studio.shoot(page, "07-config-health", row)
