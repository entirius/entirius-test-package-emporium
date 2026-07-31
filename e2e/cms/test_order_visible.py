# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""E2E: an order placed by a customer is visible to the operator in the CMS.

Self-contained: places the order through the checkout v2 API first, then logs
into the CMS and asserts the order shows up in the Orders grid. CMS_BASE_URL
is separate from pytest's --base-url, which points at the storefront.
"""

import os

import requests
from playwright.sync_api import Page, expect

CMS_BASE_URL = os.environ.get("CMS_BASE_URL", "http://localhost:8180")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

CHECKOUT_API_KEY = "entirius-docker-checkout-dev-key-2026"
CHANNEL = "default-europe"

ADDRESS = {
    "firstname": "Emporium",
    "lastname": "Operator-Check",
    "street": "Dock 7",
    "city": "Station City",
    "postcode": "00100",
    "country_code": "DE",
    "email": "tester@emporium.test",
    "dialling_code": "+49",
    "telephone": "500100200",
    "company": None,
}


def _checkout(path):
    return f"{API_BASE_URL}/api/checkout/v2/{CHANNEL}/{path}"


def _post(path, body):
    resp = requests.post(_checkout(path), json=body, headers={"X-API-KEY": CHECKOUT_API_KEY}, timeout=30)
    assert resp.status_code in (200, 201), f"POST {path} failed: {resp.status_code} {resp.text[:300]}"
    return resp.json()


def _patch(path, body):
    resp = requests.patch(_checkout(path), json=body, headers={"X-API-KEY": CHECKOUT_API_KEY}, timeout=30)
    assert resp.status_code == 200, f"PATCH {path} failed: {resp.status_code} {resp.text[:300]}"
    return resp.json()


def _place_order_via_api() -> str:
    cart = _post("carts/", {"items": [{"sku": "ENT-C003", "quantity": 1}], "currency_code": "EUR"})
    cart_id = cart["cart_id"]
    _patch(f"carts/{cart_id}/addresses/", {"shipping_address": ADDRESS, "billing_address": ADDRESS})
    _patch(f"carts/{cart_id}/shipping/", {"code": "europe-standard"})
    _patch(f"carts/{cart_id}/payment/", {"code": "banktransfer"})
    order = _post("orders/", {"cart_id": cart_id})
    assert order["order_pretty_id"], f"Order has no pretty id: {order}"
    return order["order_pretty_id"]


def test_operator_sees_placed_order(page: Page):
    pretty_id = _place_order_via_api()

    page.goto(f"{CMS_BASE_URL}/")
    page.get_by_role("textbox", name="Username").fill(ADMIN_USERNAME)
    page.get_by_role("textbox", name="Password").fill(ADMIN_PASSWORD)
    page.get_by_role("button", name="Log in").click()

    page.get_by_role("button", name="Orders").click()
    expect(page.get_by_role("gridcell", name=pretty_id)).to_be_visible()
