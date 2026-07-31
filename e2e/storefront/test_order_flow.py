# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""E2E: guest buys a product — catalog -> product -> cart -> checkout -> confirmation.

Runs against a live storefront (--base-url, default in the Makefile target) on top
of a seeded zeno stack. Fills the address form explicitly — the storefront's
"Fill test data" button is DEBUG_MODE-only and must not be a test dependency.
"""

import re

from playwright.sync_api import Page, expect

PRODUCT_NAME = "Zero-G Recliner"
PRODUCT_SKU = "ENT-C003"

BILLING = {
    "Email": "tester@emporium.test",
    "First name": "Emporium",
    "Last name": "Tester",
    "Street and number": "Dock 7",
    "Postal code": "00-100",
    "City": "Station City",
    "Phone number": "500100200",
}


def test_guest_completes_order(page: Page):
    page.goto("/catalog/office-chairs")
    page.get_by_role("link", name=PRODUCT_NAME).first.click()

    expect(page.get_by_role("heading", name=PRODUCT_NAME)).to_be_visible()
    expect(page.get_by_text(PRODUCT_SKU)).to_be_visible()
    page.get_by_role("button", name="Add to cart").click()

    # Header cart icon has no accessible name (storefront a11y gap) — enter checkout directly.
    page.goto("/checkout")
    for label, value in BILLING.items():
        page.get_by_label(label).fill(value)
    page.get_by_role("button", name="Continue to shipping").click()

    page.get_by_role("radio", name="Europe Standard").check()
    page.get_by_role("button", name="Continue to payment").click()

    page.get_by_role("radio", name="Bank Transfer").check()
    page.get_by_role("button", name="Continue to review").click()

    expect(page.get_by_role("heading", name="Shipping method")).to_be_visible()
    page.get_by_role("button", name="Place order").click()

    expect(page).to_have_url(re.compile(r"/checkout/success\?ref=\d+"))
    expect(page.get_by_role("heading", name="Order placed")).to_be_visible()
