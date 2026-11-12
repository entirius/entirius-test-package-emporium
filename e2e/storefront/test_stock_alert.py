# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""E2E: back-in-stock alerts on the live stack — the storefront form, both e-mails, the cancel page.

A shopper picks the sold-out variant of the Captain's Living Room Set, asks for an alert, gets the signup e-mail in
GreenMail and cancels through its link on the storefront. A Polish request (through the API, as the storefront sends
it) then gets its signup and, after a restock and the check, its alert; both e-mails are opened at phone (360 px) and
desktop (1280 px) width and saved into STOCK_ALERT_SHOTS_DIR (default test-results/stock-alerts) for a person to
look at; no pixel baseline.

Needs the storefront built with the stock-alerts key (zeno `make pwa`), the worker, `make mail`, and the service
container for the check (`SERVICE_CONTAINER`, zeno `make e2e` passes it).
"""

import os
import re
from pathlib import Path

from playwright.sync_api import Page, Route, expect

from entirius_tests import mail
from entirius_tests import stock_alerts as sa
from entirius_tests.api_client import ApiClient
from entirius_tests.auth import obtain_jwt_token
from entirius_tests.order_mail import part

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100")
CHANNEL = os.environ.get("PRIMARY_CHANNEL", "default-europe")
STOCK_ALERTS_KEY = os.environ.get("STOCK_ALERTS_API_KEY", "zeno-dev-only-stock-alerts-subscribe-key")
SHOTS_DIR = Path(os.environ.get("STOCK_ALERT_SHOTS_DIR", "test-results/stock-alerts"))
SHOPPER = "e2e-stock-alert@example.com"
POLISH_SHOPPER = "e2e-stock-alert-pl@example.com"
SOLD_OUT_OPTION = re.compile("Borealis Frontier")
WIDTHS = (360, 1280)


def _admin() -> tuple[ApiClient, dict]:
    api = ApiClient(base_url=API_BASE_URL)
    token = obtain_jwt_token(
        API_BASE_URL, os.environ.get("ADMIN_USERNAME", "admin"), os.environ.get("ADMIN_PASSWORD", "admin123")
    )
    return api, {"Authorization": f"Bearer {token}"}


def _clean_start(api: ApiClient, headers: dict) -> None:
    mail.purge()
    sa.reset_throttles()
    sa.set_manual_stock(api, CHANNEL, headers, 0)
    sa.cancel_waiting(api, CHANNEL, headers)


def _ask_on_the_product_page(page: Page) -> None:
    page.goto(f"/product/{sa.PARENT_URL_KEY}")
    page.get_by_role("radio", name=SOLD_OUT_OPTION).click()
    form = page.locator("form[data-stock-alert]")
    form.get_by_role("textbox", name="Email address").fill(SHOPPER)
    form.locator("[data-stock-alert-consent] button").click()
    form.get_by_role("button", name="Notify me when available").click()
    expect(page.locator('[data-stock-alert-state="saved"]')).to_be_visible()


def _polish_mails(api: ApiClient, headers: dict) -> list[str]:
    """The HTML of the Polish signup and alert e-mails; the variant is sold out again afterwards."""
    body = {**sa.request_body(POLISH_SHOPPER), "language": "pl"}
    resp = sa.subscribe(API_BASE_URL, CHANNEL, STOCK_ALERTS_KEY, body)
    assert resp.status_code == 201, f"request: {resp.status_code} {resp.text[:300]}"
    assert len(sa.wait_for_messages(POLISH_SHOPPER, 1)) == 1, "no signup e-mail"
    sa.set_manual_stock(api, CHANNEL, headers, 1)
    try:
        sa.run_check()
        messages = sa.wait_for_messages(POLISH_SHOPPER, 2)
    finally:
        sa.set_manual_stock(api, CHANNEL, headers, 0)
    assert len(messages) == 2, f"{len(messages)} e-mails, expected the signup and the alert"
    return [part(message, "text/html") for message in messages]


def _local_only(route: Route) -> None:
    """The e-mail's own pictures (the service's media) load; anything outside the stack does not."""
    if route.request.url.startswith(API_BASE_URL):
        route.continue_()
    else:
        route.abort()


def _screenshots(page: Page, name: str, html: str) -> None:
    for width in WIDTHS:
        page.set_viewport_size({"width": width, "height": 800})
        page.set_content(html, wait_until="load")
        if width == min(WIDTHS):
            overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            assert overflow <= 0, f"{name}: horizontal scroll of {overflow} px at {width} px"
        picture = page.locator('img[src*="/media/"]').first
        assert picture.evaluate("img => img.naturalWidth") > 0, f"{name}: the product picture did not load"
        page.screenshot(path=SHOTS_DIR / f"{name}-{width}.png", full_page=True)


def test_shopper_asks_for_a_sold_out_size_and_cancels(page: Page):
    api, headers = _admin()
    _clean_start(api, headers)
    _ask_on_the_product_page(page)
    signup = sa.wait_for_messages(SHOPPER, 1)
    assert len(signup) == 1, f"{len(signup)} signup e-mails, expected 1"
    link = sa.CANCEL_LINK.search(sa.text(signup[0]))
    assert link, "no cancel link in the signup e-mail"
    page.goto(f"/stock-alert/cancel?token={link.group(1)}")
    expect(page.locator('[data-stock-alert-cancel="cancelled"] h1')).to_have_text("Your request was cancelled")


def test_both_mails_render_at_phone_and_desktop_width(page: Page):
    api, headers = _admin()
    _clean_start(api, headers)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    signup, alert = _polish_mails(api, headers)
    page.route("**/*", _local_only)
    _screenshots(page, "signup-pl", signup)
    _screenshots(page, "available-pl", alert)
