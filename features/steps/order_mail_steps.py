# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Order confirmation and cancellation e-mails (`@order-mail`): the buyer places a guest order, an admin changes it,
the steps read the buyer's GreenMail mailbox. Each scenario places its own order, so the feature re-runs on one
database. `{number}`, `{numbers}` (comma-joined) and `{total}` in expected texts stand for the placed order."""

from __future__ import annotations

from behave import given, step, then, when

from entirius_tests import order_mail as om
from entirius_tests.auth import obtain_jwt_token
from entirius_tests.csv_loader import load_products

ORDER_STEP = 'the buyer places an order of "{skus}" shipped by "{shipping}" paid by "{payment}"'


def _place(context, request: om.OrderRequest) -> None:
    context.channel = context.primary_channel
    context.order = om.place_order(context.api, context.channel, request)


def _token(context) -> str:
    if not getattr(context, "order_mail_token", None):
        context.order_mail_token = obtain_jwt_token(
            context.api.base_url, context.admin_username, context.admin_password
        )
    return context.order_mail_token


def _admin(context, method: str, path: str, body: dict | None = None):
    url = om.admin_url(context.api, context.channel, f"orders/{context.order.uid}/{path}")
    return getattr(context.api, method)(url, json=body, headers={"Authorization": f"Bearer {_token(context)}"})


def _mails(context) -> list[dict]:
    return om.order_mails(context.api, context.channel, _token(context), context.order.uid)


def _expand(context, text: str) -> str:
    order = context.order
    return text.format(number=order.number, numbers=", ".join(order.numbers), total=order.total)


def _newest(context):
    """The newest message the last "the buyer receives" step saw."""
    assert getattr(context, "order_messages", None), "no e-mail read yet: use 'the buyer receives N order e-mails'"
    return context.order_messages[-1]


# --- placing the order ---


@given(ORDER_STEP + ' in language "{language}"')
def step_place_order_language(context, skus, shipping, payment, language):
    _place(context, om.OrderRequest(tuple(skus.split(",")), shipping, payment, language))


@given(ORDER_STEP + ' to the pickup point "{point}"')
def step_place_order_pickup(context, skus, shipping, payment, point):
    _place(context, om.OrderRequest(tuple(skus.split(",")), shipping, payment, pickup_point=point))


# After the longer variants: behave refuses a pattern that matches one registered before it.
@given(ORDER_STEP)
def step_place_order(context, skus, shipping, payment):
    _place(context, om.OrderRequest(tuple(skus.split(",")), shipping, payment))


# --- the admin changes the order ---


@when('an admin sets the order status to "{status}" again')
def step_admin_status_again(context, status):
    """The order already has that status: refused (400) or a no-op (200), never a server error."""
    resp = _admin(context, "patch", "status/", {"status": status})
    assert resp.status_code in (200, 400), f"repeated status change: {resp.status_code} {resp.text[:300]}"


@when('an admin sets the order status to "{status}"')
def step_admin_status(context, status):
    resp = _admin(context, "patch", "status/", {"status": status})
    assert resp.status_code == 200, f"status change failed: {resp.status_code} {resp.text[:300]}"


@when("an admin cancels the order")
def step_admin_cancel(context):
    resp = _admin(context, "post", "cancel/")
    assert resp.status_code == 200, f"cancel failed: {resp.status_code} {resp.text[:300]}"


@when('an admin resends the order\'s "{kind}" e-mail')
def step_admin_resend(context, kind):
    resp = _admin(context, "post", f"mails/{kind}/resend/")
    assert resp.status_code == 202, f"resend failed: {resp.status_code} {resp.text[:300]}"


# --- the buyer's mailbox and the order's e-mail log ---


@then("the buyer receives {count:d} order e-mails")
def step_buyer_receives(context, count):
    context.order_messages = om.order_messages(context.order, count)
    assert len(context.order_messages) == count, (
        f"expected {count} e-mails about {context.order.number}, found {len(context.order_messages)}: "
        f"{[om.subject(message) for message in context.order_messages]}"
    )


@then("the buyer receives no order e-mail")
def step_buyer_receives_none(context):
    """The log row is written in the request that changes the order, so an empty log means nothing is coming."""
    assert _mails(context) == [], f"the order has e-mails: {_mails(context)}"
    assert om.order_messages(context.order, 0) == [], "an e-mail about the order reached the buyer's mailbox"


@step('the order\'s "{kind}" e-mail was sent {attempts:d} times')
def step_mail_sent_times(context, kind, attempts):
    row = om.wait_for_mail_row(lambda: _mails(context), kind, attempts)
    assert row.get("status") == "sent" and row.get("attempts") == attempts, f"{kind} e-mail row: {row}"


@then('the newest order e-mail subject is "{expected}"')
def step_newest_subject(context, expected):
    actual = om.subject(_newest(context))
    assert actual == _expand(context, expected), f"subject {actual!r}, expected {_expand(context, expected)!r}"


@then('the newest order e-mail text contains "{expected}"')
def step_newest_text(context, expected):
    text = om.part(_newest(context), "text/plain")
    assert _expand(context, expected) in text, f"{_expand(context, expected)!r} not in the text part:\n{text}"


@then("the newest order e-mail names every ordered item")
def step_newest_items(context):
    """Item names come from the catalog CSV, in the order's language."""
    text = om.part(_newest(context), "text/plain")
    rows = {row["sku"]: row for row in load_products(context.test_package_path, context.channel)}
    names = [rows[sku][f"name {context.order.language}"] for sku in context.order.skus]
    missing = [name for name in names if name not in text]
    assert not missing, f"item names missing from the e-mail: {missing}"


@then("the newest order e-mail has a text and an HTML part")
def step_newest_multipart(context):
    message = _newest(context)
    assert message.get_content_type() == "multipart/alternative", message.get_content_type()
    assert om.part(message, "text/plain").strip(), "no text part"
    assert om.part(message, "text/html").strip(), "no HTML part"
