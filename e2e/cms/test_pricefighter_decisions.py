# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""E2E smoke: the PriceFighter panel shows the computed decision workload.

The seed leaves calibrated inputs (costs, baseline, rules, observations), so the
gap-analysis list must render rows with a `compete` recommendation. Read-only.
"""

from playwright.sync_api import Page, expect

from entirius_tests.cms_e2e import require_module

pytestmark = require_module("pricefighter")


def test_pricefighter_decisions_visible(admin_page: Page):
    admin_page.get_by_role("button", name="PriceFighter").click()
    # The gap list computes live from seeded inputs — ENT-C002 competes at 287.00.
    expect(admin_page.get_by_text("ENT-C002").first).to_be_visible(timeout=15000)
    expect(admin_page.get_by_text("compete", exact=False).first).to_be_visible()
