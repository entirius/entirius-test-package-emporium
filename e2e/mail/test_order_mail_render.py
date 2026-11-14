# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Rendering check of the order e-mails: a Polish transfer confirmation, a split confirmation and a cancellation.

Self-contained: places its own orders through the checkout v2 API, reads the HTML part from GreenMail (zeno:
make mail), opens it at phone (360 px) and desktop (1280 px) width and saves a screenshot of each into
MAIL_SHOTS_DIR (default test-results/order-mail) for a person to look at; no pixel baseline. Images are answered
locally, so the check never reaches the logo host. Needs the seeded stack and a running worker, no frontend.
"""

import os
import struct
import zlib
from pathlib import Path

import pytest
from playwright.sync_api import Page, Route, expect

from entirius_tests import mail
from entirius_tests import order_mail as om
from entirius_tests.api_client import ApiClient
from entirius_tests.auth import obtain_jwt_token
from entirius_tests.csv_loader import load_products

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100")
CHANNEL = os.environ.get("PRIMARY_CHANNEL", "default-europe")
SHOTS_DIR = Path(os.environ.get("MAIL_SHOTS_DIR", "test-results/order-mail"))
PACKAGE = Path(__file__).resolve().parents[2] / "package"
WIDTHS = (360, 1280)
LOGO_SIZE = (200, 60)
CASES = {
    "pl-transfer-confirmation": om.OrderRequest(("ENT-O001",), "europe-standard", "banktransfer", "pl"),
    "split-confirmation": om.OrderRequest(("ENT-S005", "ENT-B002"), "europe-standard", "banktransfer"),
    "cancellation": om.OrderRequest(("ENT-O001",), "europe-standard", "banktransfer"),
}


def _cancel(api: ApiClient, order: om.PlacedOrder) -> None:
    token = obtain_jwt_token(
        API_BASE_URL, os.environ.get("ADMIN_USERNAME", "admin"), os.environ.get("ADMIN_PASSWORD", "admin123")
    )
    headers = {"Authorization": f"Bearer {token}"}
    for path, body in (("status/", {"status": "confirmed"}), ("cancel/", None)):
        url = om.admin_url(api, CHANNEL, f"orders/{order.uid}/{path}")
        method = api.patch if body else api.post
        assert method(url, json=body, headers=headers).status_code == 200, f"{path} refused for {order.number}"


def _order_mail(name: str) -> tuple[om.PlacedOrder, str]:
    """Places the case's order into an empty mailbox; returns it and the HTML part of its newest e-mail."""
    api = ApiClient(base_url=API_BASE_URL)
    mail.purge()
    order = om.place_order(api, CHANNEL, CASES[name])
    expected = 1
    if name == "cancellation":
        om.order_messages(order, 1)
        _cancel(api, order)
        expected = 2
    messages = om.order_messages(order, expected)
    assert len(messages) == expected, f"{name}: {len(messages)} e-mails, expected {expected}"
    return order, om.part(messages[-1], "text/html")


def _item_names(order: om.PlacedOrder) -> list[str]:
    rows = {row["sku"]: row for row in load_products(str(PACKAGE), CHANNEL)}
    return [rows[sku][f"name {order.language}"] for sku in order.skus]


def _png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """A solid-colour PNG: stands in for every image of the e-mail (the logo), so it shows in the screenshots."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    rows = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


LOGO = _png(*LOGO_SIZE, (64, 64, 64))


def _serve_logo(route: Route) -> None:
    route.fulfill(status=200, content_type="image/png", body=LOGO)


@pytest.mark.parametrize("name", list(CASES))
def test_order_mail_renders(page: Page, name: str):
    order, html = _order_mail(name)
    assert html, f"{name}: no HTML part"
    page.route("**/*", _serve_logo)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        page.set_viewport_size({"width": width, "height": 800})
        page.set_content(html)
        _assert_rendered(page, order, width)
        page.screenshot(path=SHOTS_DIR / f"{name}-{width}.png", full_page=True)


def _assert_rendered(page: Page, order: om.PlacedOrder, width: int) -> None:
    if width == min(WIDTHS):
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 0, f"horizontal scroll of {overflow} px at {width} px"
    expect(page.locator("img").first).to_be_visible()
    for item in _item_names(order):
        expect(page.get_by_text(item).first).to_be_visible()
    expect(page.get_by_text(order.total).last).to_be_visible()
