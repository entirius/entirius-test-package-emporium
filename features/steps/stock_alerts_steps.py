# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Back-in-stock alerts (`features/stock_alerts/`): requests, restocks, the check, the e-mails of one address.

Every address of the feature is its own GreenMail mailbox and receives nothing but back-in-stock e-mails, so its
message count is the e-mail count. `context.mail_counts` keeps the count each address was last seen with.
"""

from __future__ import annotations

import time

from behave import given, then, when

from entirius_tests import order_mail as om
from entirius_tests import stock_alerts as sa
from entirius_tests.auth import obtain_jwt_token


def _admin_headers(context) -> dict[str, str]:
    """The admin's bearer token, one per scenario; the shared session keeps its own auth (a viewer, or none)."""
    if "stock_alerts_admin" not in context.raw_tokens:
        token = obtain_jwt_token(context.api.base_url, context.admin_username, context.admin_password)
        context.raw_tokens["stock_alerts_admin"] = token
    return {"Authorization": f"Bearer {context.raw_tokens['stock_alerts_admin']}"}


def _requests_of(context, params: dict) -> list[dict]:
    return sa.admin_requests(context.api, context.channel, _admin_headers(context), params)


def _set_manual_stock(context, quantity: int) -> None:
    sa.set_manual_stock(context.api, context.channel, _admin_headers(context), quantity)


def _ask(context, address: str, **body: str) -> None:
    payload = sa.request_body(address, **body)
    context.response = sa.subscribe(context.api.base_url, context.channel, context.stock_alerts_api_key, payload)
    context.response_data = context.response.json()


def _count_is(context, address: str, count: int) -> None:
    found = sa.wait_for_messages(address, count)
    assert len(found) == count, f"{address}: {len(found)} e-mails, expected {count}"
    context.mail_counts[address] = count


# --- Setup ---


@given("no back-in-stock request waits for the sold-out variant")
def step_no_waiting(context):
    """Cancels the waiting requests of the variant (admin API), sets its manual stock to 0, resets the throttles."""
    context.mail_counts = {}
    sa.reset_throttles()
    _set_manual_stock(context, 0)
    sa.cancel_waiting(context.api, context.channel, _admin_headers(context))


@given('"{address}" waits for the sold-out variant')
def step_waits(context, address):
    _ask(context, address)
    assert context.response.status_code == 201, f"request: {context.response.status_code} {context.response.text}"
    _count_is(context, address, context.mail_counts.get(address, 0) + 1)
    context.saved["request_id"] = _requests_of(context, {"sku": sa.SOLD_OUT_SKU, "search": address})[0]["id"]


@given("the sold-out variant gets {quantity:d} piece in the manual warehouse")
@when("the sold-out variant gets {quantity:d} piece in the manual warehouse")
def step_restock(context, quantity):
    _set_manual_stock(context, quantity)


@then("the sold-out variant is sold out again")
def step_sold_out_again(context):
    _set_manual_stock(context, 0)


@given("a guest order reserves the piece of the sold-out variant")
def step_order(context):
    request = om.OrderRequest((sa.SOLD_OUT_SKU,), "europe-standard", "banktransfer")
    context.saved["order"] = om.place_order(context.api, context.channel, request)


@when("the guest order is cancelled")
def step_cancel_order(context):
    order = context.saved.pop("order")
    sa.cancel_order(context.api, context.channel, _admin_headers(context), order.uid)


# --- Storefront calls ---


@when('"{address}" asks for an alert on the sold-out variant')
def step_ask_sold_out(context, address):
    _ask(context, address)


@when('"{address}" asks for an alert on the in-stock variant')
def step_ask_in_stock(context, address):
    _ask(context, address, sku=sa.IN_STOCK_SKU)


@when('"{address}" asks for an alert on the sold-out variant with the honeypot filled')
def step_ask_honeypot(context, address):
    _ask(context, address, website="https://spam.example")


@when('"{address}" cancels by the link of the signup e-mail')
def step_cancel_by_link(context, address):
    token = sa.cancel_token(sa.messages(address)[0])
    url = context.api.url(f"api/stock-alerts/v2/{context.channel}/subscriptions/cancel/")
    context.response = context.api.post(url, json={"token": token})
    context.response_data = context.response.json()


@when("the restock check runs")
def step_check(context):
    sa.run_check()


# --- E-mails ---


@then('"{address}" receives {count:d} back-in-stock e-mail')
@then('"{address}" receives {count:d} back-in-stock e-mails')
def step_receives(context, address, count):
    _count_is(context, address, count)


@then('"{address}" receives no further back-in-stock e-mail')
def step_no_further(context, address):
    expected = context.mail_counts.get(address, 0)
    time.sleep(sa.NO_MAIL_WAIT_S)
    found = len(sa.messages(address))
    assert found == expected, f"{address}: {found} e-mails, expected still {expected}"


@then('the newest back-in-stock e-mail of "{address}" names the product and has a cancel link')
def step_signup_mail(context, address):
    message = sa.messages(address)[-1]
    assert sa.PRODUCT_NAME in sa.text(message), f"no {sa.PRODUCT_NAME!r} in the e-mail"
    assert sa.cancel_token(message)


@then('the newest back-in-stock e-mail of "{address}" names the size and links to the variant')
def step_alert_mail(context, address):
    body = sa.text(sa.messages(address)[-1])
    assert sa.VARIANT_LINE in body, f"no {sa.VARIANT_LINE!r} in the e-mail"
    assert f"variant={sa.SOLD_OUT_SKU}" in body, "no link to the variant in the e-mail"


# --- Admin and agreements ---


@then('{count:d} back-in-stock request of "{address}" is waiting')
@then('{count:d} back-in-stock requests of "{address}" are waiting')
def step_waiting_count(context, count, address):
    rows = _requests_of(context, {"sku": sa.SOLD_OUT_SKU, "status": "waiting", "search": address})
    assert len(rows) == count, f"{address}: {len(rows)} waiting requests, expected {count}"


@then('the back-in-stock request of "{address}" is "{status}"')
def step_request_status(context, address, status):
    rows = _requests_of(context, {"sku": sa.SOLD_OUT_SKU, "search": address})
    row = next(row for row in rows if row["id"] == context.saved["request_id"])
    assert row["status"] == status, f"request {row['id']}: {row['status']}, expected {status}"


@then("the demand row of the sold-out variant counts {count:d} waiting request")
def step_demand(context, count):
    rows = [row for row in context.response_data["results"] if row["sku"] == sa.SOLD_OUT_SKU]
    assert rows, f"no demand row for {sa.SOLD_OUT_SKU}: {context.response_data}"
    assert rows[0]["waiting"] == count, f"waiting {rows[0]['waiting']}, expected {count}"


@when('the viewer cancels the back-in-stock request of "{address}"')
def step_viewer_cancel(context, address):
    path = f"api/stock-alerts/v2/admin/{context.channel}/subscriptions/{context.saved['request_id']}/cancel/"
    url = context.api.url(path)
    context.response = context.api.post(url)


@then('the saved back-in-stock request is cancelled with the reason "{reason}" and holds no address')
def step_erased(context, reason):
    rows = _requests_of(context, {"sku": sa.SOLD_OUT_SKU, "status": "cancelled"})
    row = next(row for row in rows if row["id"] == context.saved["request_id"])
    assert row["cancel_reason"] == reason, f"cancel_reason {row['cancel_reason']!r}, expected {reason!r}"
    assert "@example.com" not in row["email"], f"address kept: {row['email']}"


@then('the consent "{slug}" of "{address}" is "{status}" in agreements')
def step_consent(context, slug, address, status):
    url = context.api.url(f"api/agreements/v2/admin/people/{address}/")
    resp = context.api.get(url, headers=_admin_headers(context))
    assert resp.status_code == 200, f"person detail: {resp.status_code} {resp.text[:300]}"
    current = resp.json()["current_status"].get(slug, {})
    assert current.get("status") == status, f"consent {slug} of {address}: {current}, expected {status}"
