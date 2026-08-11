# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""E2E smoke: the Atlas panel serves the seeded operator workload.

The seed (Step 6x) leaves atl-nova products in `queued` — the operator opens the
Atlas panel, sees the sources list, and the Review Queue lists the queued items.
"""

from playwright.sync_api import Page, expect

from entirius_tests.cms_e2e import CMS_BASE_URL, require_module

pytestmark = require_module("atlas")


def test_atlas_sources_and_review_queue(admin_page: Page):
    admin_page.get_by_role("button", name="Atlas").click()
    # Sources list: the seeded procurement source is visible.
    expect(admin_page.get_by_text("NovaTrade Atlas").first).to_be_visible(timeout=10000)

    # Review queue defaults to `queued` — the seed leaves ATL-N005..N009 there.
    admin_page.goto(f"{CMS_BASE_URL}/atlas/review?mode=list")
    expect(admin_page.get_by_text("Walnut Magazine Rack").first).to_be_visible(timeout=10000)
