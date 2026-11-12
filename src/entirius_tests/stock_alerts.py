# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Back-in-stock alerts on the live stack: requests through the storefront route, stock through the QMS warehouse API,
the restock check through the service's management shell, and the e-mails of one address in GreenMail.

Shared by the `@stock-alerts` steps and the storefront e2e. The check runs in the service container
(`SERVICE_CONTAINER`, zeno `make bdd` passes it): the module has no HTTP route for it and beat runs it every 5 minutes.
"""

from __future__ import annotations

import email
import os
import re
import subprocess
import time
from email.message import Message
from urllib.parse import unquote

import requests

from entirius_tests import mail
from entirius_tests.api_client import ApiClient
from entirius_tests.order_mail import admin_url, part, subject

SOLD_OUT_SKU = "ENT-S004"
IN_STOCK_SKU = "ENT-S001"
PARENT_URL_KEY = "captains-living-room-set"
# What the e-mail card shows: the parent's name (part of it: the apostrophe is escaped) and the variant's series.
PRODUCT_NAME = "Living Room Set"
VARIANT_LINE = "Borealis Frontier"
# The manual warehouse of the channel: a scenario raises the sold-out variant there and sets it back to 0.
MANUAL_WAREHOUSE = "manual-{channel}"
CONSENT_TEXT = "Email me once when this product is back in stock."
# Right after a seed the worker still drains the seed's tasks: a first e-mail can wait a minute in the queue.
MAIL_TIMEOUT_S = 120
# How long "no e-mail" is watched for: the send tasks of a check are queued at once and run within seconds.
NO_MAIL_WAIT_S = 8
CHECK_LOCK_RETRY_S = 2
CHECK_ATTEMPTS = 60
CANCEL_LINK = re.compile(r"stock-alert/cancel\?token=([^\s\"'&<>]+)")
_CHECK = "from django_stock_alerts.tasks.check import check\nprint('ENQUEUED', check())\n"
# DRF throttle counters of the module (django-redis default cache): a scenario starts with fresh ones.
_RESET_THROTTLES = (
    "from django.core.cache import cache\nprint('DELETED', cache.delete_pattern('throttle_stock_alerts_*'))\n"
)


def service_shell(code: str) -> str:
    """Runs `code` in `manage.py shell` of the service container; returns its stdout."""
    container = os.environ.get("SERVICE_CONTAINER", "")
    if not container:
        raise AssertionError("SERVICE_CONTAINER is not set - run the suite through zeno `make bdd`")
    cmd = ["docker", "exec", "-i", container, "python", "manage.py", "shell"]
    done = subprocess.run(cmd, input=code, capture_output=True, text=True, timeout=180, check=False)  # noqa: S603 — a fixed argv
    if done.returncode != 0:
        raise AssertionError(f"manage.py shell failed: {done.stderr[-800:]}")
    return done.stdout


def run_check() -> int:
    """The restock check once, now; waits while a beat run holds its lock. Returns the alerts it enqueued."""
    for _ in range(CHECK_ATTEMPTS):
        found = re.search(r"ENQUEUED (\S+)", service_shell(_CHECK))
        if not found:
            raise AssertionError("the check printed no result")
        if found.group(1) != "None":
            return int(found.group(1))
        time.sleep(CHECK_LOCK_RETRY_S)
    raise AssertionError("the restock check stayed locked (another run holds django_stock_alerts:check)")


def reset_throttles() -> None:
    service_shell(_RESET_THROTTLES)


def subscribe(base_url: str, channel: str, key: str, body: dict) -> requests.Response:
    """The storefront's call: `X-API-KEY`, no JWT."""
    url = f"{base_url.rstrip('/')}/api/stock-alerts/v2/{channel}/subscriptions/"
    return requests.post(url, json=body, headers={"X-API-KEY": key}, timeout=30)


def request_body(address: str, sku: str = SOLD_OUT_SKU, website: str = "") -> dict:
    return {
        "email": address,
        "sku": sku,
        "language": "en",
        "country": "",
        "consent": True,
        "consent_text": CONSENT_TEXT,
        "website": website,
    }


def messages(address: str) -> list[Message]:
    """The address's messages in GreenMail, oldest first."""
    try:
        items = mail.list_messages(address)
    except requests.HTTPError:  # GreenMail knows an address only after its first message
        return []
    return [email.message_from_string(item["mimeMessage"]) for item in items]


def wait_for_messages(address: str, count: int, timeout_s: float = MAIL_TIMEOUT_S) -> list[Message]:
    """Waits until the address has at least `count` messages (or the timeout); returns what it has."""
    deadline = time.monotonic() + timeout_s
    while len(found := messages(address)) < count and time.monotonic() < deadline:
        time.sleep(0.5)
    return found


def text(message: Message) -> str:
    return part(message, "text/plain")


def cancel_token(message: Message) -> str:
    found = CANCEL_LINK.search(text(message))
    if not found:
        raise AssertionError(f"no cancel link in {subject(message)!r}")
    return unquote(found.group(1))


def admin_requests(api: ApiClient, channel: str, headers: dict, params: dict) -> list[dict]:
    """Rows of the admin list of requests (one page of 100)."""
    url = api.url(f"api/stock-alerts/v2/admin/{channel}/subscriptions/")
    resp = api.get(url, params={"page_size": 100, **params}, headers=headers)
    if resp.status_code != 200:
        raise AssertionError(f"subscriptions list: {resp.status_code} {resp.text[:300]}")
    return resp.json()["results"]


def cancel_waiting(api: ApiClient, channel: str, headers: dict) -> None:
    """Cancels every waiting request of the sold-out variant: a wave then reaches the requests of this run first."""
    for row in admin_requests(api, channel, headers, {"sku": SOLD_OUT_SKU, "status": "waiting"}):
        url = api.url(f"api/stock-alerts/v2/admin/{channel}/subscriptions/{row['id']}/cancel/")
        resp = api.post(url, headers=headers)
        if resp.status_code != 200:
            raise AssertionError(f"cancel {row['id']}: {resp.status_code} {resp.text[:300]}")


def set_manual_stock(api: ApiClient, channel: str, headers: dict, quantity: int) -> None:
    """The sold-out variant's quantity in the channel's manual warehouse (QMS admin API)."""
    warehouse = MANUAL_WAREHOUSE.format(channel=channel)
    url = api.url(f"api/qms/v2/admin/warehouses/{warehouse}/stock/edit/")
    body = {"items": [{"sku": SOLD_OUT_SKU, "quantity": quantity}]}
    resp = api.patch(url, json=body, headers=headers)
    if resp.status_code != 200:
        raise AssertionError(f"stock edit: {resp.status_code} {resp.text[:300]}")


def cancel_order(api: ApiClient, channel: str, headers: dict, uid: str) -> None:
    """Confirms, then cancels the order: its reservation is released, so the piece is back."""
    for path, body in (("status/", {"status": "confirmed"}), ("cancel/", None)):
        url = admin_url(api, channel, f"orders/{uid}/{path}")
        resp = (api.patch if body else api.post)(url, json=body, headers=headers)
        if resp.status_code != 200:
            raise AssertionError(f"order {path}: {resp.status_code} {resp.text[:300]}")
