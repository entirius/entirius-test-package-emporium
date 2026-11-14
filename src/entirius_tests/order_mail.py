# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Order e-mails on the live stack: place a guest order through checkout v2, drive it through the admin API and read
the buyer's mailbox in GreenMail. Shared by the `@order-mail` steps and the rendering check in `e2e/mail/`.

Admin calls carry their own bearer token, so the shared session stays anonymous and the cart stays a guest cart.
"""

from __future__ import annotations

import email
import time
from collections.abc import Callable
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import Message

from entirius_tests import mail
from entirius_tests.api_client import ApiClient

BUYER_EMAIL = "bdd-order-mail@emporium.test"
CURRENCY = "EUR"
# Right after a seed the worker still drains the seed's tasks: an order e-mail can wait a minute in the queue.
MAIL_TIMEOUT_S = 120
# Synthetic guest; the mailbox is the buyer's own GreenMail user (GreenMail creates one per recipient).
BUYER_ADDRESS = {
    "firstname": "Emporium",
    "lastname": "Buyer",
    "street": "Dock 7",
    "city": "Station City",
    "postcode": "00100",
    "country_code": "DE",
    "email": BUYER_EMAIL,
    "dialling_code": "+49",
    "telephone": "500100200",
    "company": None,
}


@dataclass(frozen=True)
class OrderRequest:
    skus: tuple[str, ...]
    shipping: str
    payment: str
    language: str = "en"
    pickup_point: str | None = None


@dataclass(frozen=True)
class PlacedOrder:
    uid: str
    number: str
    numbers: tuple[str, ...]
    total: str
    language: str
    skus: tuple[str, ...]


def _call(api: ApiClient, method: str, url: str, body: dict | None = None, **kwargs: object) -> dict:
    resp = getattr(api, method)(url, json=body, **kwargs)
    if resp.status_code not in (200, 201, 202):
        raise AssertionError(f"{method.upper()} {url}: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def place_order(api: ApiClient, channel: str, request: OrderRequest) -> PlacedOrder:
    """Cart → addresses → shipping → payment → order; the total is the cart's, formatted like the e-mail."""
    base = api.checkout_v2_url(channel)
    items = [{"sku": sku, "quantity": 1} for sku in request.skus]
    body = {"items": items, "currency_code": CURRENCY, "language_code": request.language}
    cart_id = _call(api, "post", f"{base}carts/", body)["cart_id"]
    addresses = {"shipping_address": BUYER_ADDRESS, "billing_address": BUYER_ADDRESS}
    _call(api, "patch", f"{base}carts/{cart_id}/addresses/", addresses)
    _call(api, "patch", f"{base}carts/{cart_id}/shipping/", _shipping(request))
    cart = _call(api, "patch", f"{base}carts/{cart_id}/payment/", {"code": request.payment})
    if cart["validation_status"] != "valid":
        raise AssertionError(f"cart not valid: {cart}")
    order = _call(api, "post", f"{base}orders/", {"cart_id": cart_id})
    numbers = tuple(order["split_orders_pretty_ids"]) or (order["order_pretty_id"],)
    total = f"{cart['total_gross']} {CURRENCY}"
    return PlacedOrder(order["order_id"], order["order_pretty_id"], numbers, total, request.language, request.skus)


def _shipping(request: OrderRequest) -> dict:
    if request.pickup_point is None:
        return {"code": request.shipping}
    point = {"code": "BDD-POINT-1", "name": request.pickup_point, "address": "Dock 7", "city": "Station City"}
    return {"code": request.shipping, "delivery_point": {**point, "postcode": "00100"}}


def admin_url(api: ApiClient, channel: str, path: str) -> str:
    return api.url(f"api/checkout/v2/admin/{channel}/{path}")


def order_mails(api: ApiClient, channel: str, token: str, uid: str) -> list[dict]:
    """`mails` of the admin order detail: one row per e-mail kind of the order."""
    headers = {"Authorization": f"Bearer {token}"}
    return _call(api, "get", admin_url(api, channel, f"orders/{uid}/"), headers=headers)["mails"]


def wait_for_mail_row(rows_of: Callable[[], list[dict]], kind: str, attempts: int) -> dict:
    """Poll until the row of `kind` is `sent` after `attempts` sends; returns the last row seen (or {})."""
    deadline, row = time.monotonic() + MAIL_TIMEOUT_S, {}
    while time.monotonic() < deadline:
        row = next((each for each in rows_of() if each["kind"] == kind), {})
        if row.get("status") == "sent" and row.get("attempts") == attempts:
            return row
        time.sleep(0.5)
    return row


def order_messages(order: PlacedOrder, count: int) -> list[Message]:
    """The buyer's messages about this order (its number in the subject), oldest first, after waiting up to
    MAIL_TIMEOUT_S for `count` of them. A late e-mail of another order never counts."""
    deadline = time.monotonic() + MAIL_TIMEOUT_S
    while len(found := _messages_about(order)) < count and time.monotonic() < deadline:
        time.sleep(0.5)
    return found


def _messages_about(order: PlacedOrder) -> list[Message]:
    messages = [email.message_from_string(item["mimeMessage"]) for item in mail.list_messages(BUYER_EMAIL)]
    return [message for message in messages if order.number in subject(message)]


def subject(message: Message) -> str:
    return str(make_header(decode_header(message["Subject"] or "")))


def part(message: Message, content_type: str) -> str:
    """The decoded body of the first part of that type; '' when the message has none."""
    for each in message.walk():
        if each.get_content_type() == content_type:
            return each.get_payload(decode=True).decode(each.get_content_charset() or "utf-8")
    return ""
