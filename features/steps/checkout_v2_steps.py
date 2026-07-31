# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for the checkout v2 guest flow (cart -> address -> shipping -> payment -> order)."""

from behave import given, then, when

from entirius_tests.csv_loader import load_products

# Synthetic guest identity; country_code comes from the scenario.
_TEST_ADDRESS = {
    "firstname": "Emporium",
    "lastname": "Tester",
    "street": "Dock 7",
    "city": "Station City",
    "postcode": "00100",
    "email": "tester@emporium.test",
    "dialling_code": "+49",
    "telephone": "500100200",
    "company": None,
}


def _v2_url(context, path):
    return context.api.checkout_v2_url(context.channel, path)


def _store_response(context, resp):
    context.response = resp
    try:
        context.response_data = resp.json()
    except ValueError:
        context.response_data = {}


def _create_cart(context, sku, qty, currency):
    body = {"items": [{"sku": sku, "quantity": qty}], "currency_code": currency}
    resp = context.api.post(_v2_url(context, "carts/"), json=body)
    assert resp.status_code == 201, f"Cart create failed: {resp.status_code} {resp.text[:300]}"
    return resp.json()["cart_id"]


def _set_addresses(context, cart_id, country_code):
    address = {**_TEST_ADDRESS, "country_code": country_code}
    body = {"shipping_address": address, "billing_address": address}
    resp = context.api.patch(_v2_url(context, f"carts/{cart_id}/addresses/"), json=body)
    assert resp.status_code == 200, f"Address set failed: {resp.status_code} {resp.text[:300]}"


@given('I create a v2 cart with product "{sku}" quantity {qty:d} in currency "{currency}"')
def step_create_v2_cart(context, sku, qty, currency):
    context.cart_id = _create_cart(context, sku, qty, currency)


@given('the v2 cart addresses are set to country "{country_code}"')
def step_set_v2_addresses(context, country_code):
    _set_addresses(context, context.cart_id, country_code)


@when("I GET the v2 shipping methods for the cart")
def step_get_v2_shipping_methods(context):
    _store_response(context, context.api.get(_v2_url(context, f"carts/{context.cart_id}/shipping-methods/")))


@then("the v2 shipping methods list should not be empty")
def step_shipping_methods_not_empty(context):
    assert isinstance(context.response_data, list), f"Expected a list, got: {context.response_data}"
    assert context.response_data, "Shipping methods list is empty"


@when('I select the v2 shipping method "{code}"')
def step_select_v2_shipping(context, code):
    resp = context.api.patch(_v2_url(context, f"carts/{context.cart_id}/shipping/"), json={"code": code})
    assert resp.status_code == 200, f"Shipping select failed: {resp.status_code} {resp.text[:300]}"
    _store_response(context, resp)


@when('I select the v2 payment method "{code}"')
def step_select_v2_payment(context, code):
    resp = context.api.patch(_v2_url(context, f"carts/{context.cart_id}/payment/"), json={"code": code})
    assert resp.status_code == 200, f"Payment select failed: {resp.status_code} {resp.text[:300]}"
    _store_response(context, resp)


@then('the v2 cart validation status should be "{status}"')
def step_v2_cart_validation_status(context, status):
    actual = context.response_data.get("validation_status")
    assert actual == status, f"Expected validation_status '{status}', got '{actual}'"


@when("I create an order from the v2 cart")
def step_create_v2_order(context):
    _store_response(context, context.api.post(_v2_url(context, "orders/"), json={"cart_id": context.cart_id}))


@then('the order should have status "{status}" and a pretty id')
def step_order_created(context, status):
    data = context.response_data
    assert data.get("order_status") == status, f"Expected order_status '{status}', got: {data}"
    assert data.get("order_pretty_id"), f"Missing order_pretty_id in: {data}"


@then('every v2 checkout country has at least one shipping method in currency "{currency}"')
def step_every_country_has_shipping(context, currency):
    resp = context.api.get(_v2_url(context, "countries/"))
    assert resp.status_code == 200, f"Countries failed: {resp.status_code} {resp.text[:300]}"
    countries = [c["code"] for c in resp.json()["countries"]]
    assert countries, "Channel offers no checkout countries"

    sku = load_products(context.test_package_path, context.channel)[0]["sku"]
    missing = []
    for country_code in countries:
        cart_id = _create_cart(context, sku, 1, currency)
        _set_addresses(context, cart_id, country_code)
        methods = context.api.get(_v2_url(context, f"carts/{cart_id}/shipping-methods/")).json()
        if not methods:
            missing.append(country_code)
    assert not missing, f"Countries without any shipping method: {missing}"
