# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Behave environment hooks for API testing."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from entirius_tests.api_client import ApiClient
from entirius_tests.munin import MODULE_TAGS, MUNIN_REGISTRY_PATH, parse_modules

logger = logging.getLogger("entirius_tests")


def probe_installed_modules(api: ApiClient) -> set[str] | None:
    """Module keys from the public munin registry; None when the probe fails
    (backend down / munin absent / empty registry) — then nothing is skipped and
    features fail with their real errors instead of a silent skip."""
    try:
        resp = api.get(api.url(MUNIN_REGISTRY_PATH))
        if resp.status_code == 200:
            modules = parse_modules(resp.json())
            if modules is None:
                logger.warning("munin registry empty/unshaped — module-tagged features will run")
            return modules
        logger.warning("munin probe HTTP %s — module-tagged features will run", resp.status_code)
    except Exception as exc:  # noqa: BLE001 — any probe failure means "don't skip"
        logger.warning("munin module probe failed (%s) — module-tagged features will run", exc)
    return None


def discover_channels(package_path: str) -> list[str]:
    """Auto-discover channels from products--{channel}.csv filenames."""
    path = Path(package_path)
    channels = []
    for csv_file in sorted(path.glob("products--*.csv")):
        name = csv_file.stem  # e.g. "products--default-europe"
        channel = name.split("--", 1)[1]
        channels.append(channel)
    return channels


def before_all(context):
    """Set up API client from env vars or behave userdata."""
    ud = context.config.userdata

    # Direct stderr handler — behave won't capture this
    handler = logging.StreamHandler(sys.__stderr__)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)

    context.api = ApiClient(
        base_url=os.environ.get("API_BASE_URL", ud.get("api_base_url", "http://localhost:8000")),
        api_version=os.environ.get("API_VERSION", ud.get("api_version", "1")),
    )

    context.test_package_path = os.environ.get(
        "TEST_PACKAGE_PATH",
        ud.get("test_package_path", "package"),
    )

    context.admin_username = os.environ.get("ADMIN_USERNAME", ud.get("admin_username", "admin"))
    context.admin_password = os.environ.get("ADMIN_PASSWORD", ud.get("admin_password", "admin123"))

    context.test_username = os.environ.get("TEST_USERNAME", ud.get("test_username", "testuser"))
    context.test_password = os.environ.get("TEST_PASSWORD", ud.get("test_password", "testuser123"))

    # Channels: env var > behave.ini > auto-discover from CSV filenames
    channels_str = os.environ.get("CHANNELS", ud.get("channels", ""))
    if channels_str:
        context.channels = [c.strip() for c in channels_str.split(",") if c.strip()]
    else:
        context.channels = discover_channels(context.test_package_path)

    primary = os.environ.get("PRIMARY_CHANNEL", ud.get("primary_channel", ""))
    if primary:
        context.primary_channel = primary
    elif context.channels:
        context.primary_channel = context.channels[0]
    else:
        context.primary_channel = "default-europe"

    context.installed_modules = probe_installed_modules(context.api)


def before_feature(context, feature):
    """Skip module-tagged features when the backend does not adopt the module."""
    if context.installed_modules is None:
        return
    for tag in MODULE_TAGS:
        if tag in feature.tags and tag not in context.installed_modules:
            feature.skip(reason=f"module '{tag}' not installed (munin registry)")
            return


def before_scenario(context, scenario):
    """Reset per-scenario state."""
    context.response = None
    context.response_data = None
    context.channel = None
    context.csv_data = None
    context.attr_type = None
    context.saved = {}
    context.api.clear_auth_token()


def after_all(context):
    """Post-run warnings for products missing price or stock data."""
    warnings = []
    for channel in context.channels:
        url = context.api.matrix_url(channel, "products/")
        try:
            resp = context.api.get(url, params={"limit": 200, "language": "en", "currency": "EUR"})
            if resp.status_code != 200:
                continue
            data = resp.json().get("data", [])
            if not data:
                continue
        except Exception:
            continue

        for p in data:
            sku = p.get("sku", "?")
            ptype = p.get("product_type", "?")
            price = p.get("final_price")
            price_range = p.get("price_range")
            on_stock = p.get("on_stock")
            media = p.get("media", [])

            has_price = price is not None or (isinstance(price_range, dict) and price_range.get("from"))
            if not has_price:
                warnings.append(f"[{channel}] {sku} ({ptype}): no price data")
            if on_stock is False:
                warnings.append(f"[{channel}] {sku} ({ptype}): out of stock")
            if not media:
                warnings.append(f"[{channel}] {sku} ({ptype}): no images")
            elif any(not item.get("source_set") for item in media if item.get("type") == "picture"):
                warnings.append(f"[{channel}] {sku} ({ptype}): images without thumbnails")

    if warnings:
        logger.warning("")
        logger.warning("--- Product Data Warnings ---")
        for w in warnings:
            logger.warning("  %s", w)
        logger.warning("  (%d warnings total)", len(warnings))
        logger.warning("-----------------------------")
