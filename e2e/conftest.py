# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Suite-wide e2e fixtures. `E2E_DEVICE` (a Playwright device name, e.g. "iPhone 14") emulates that
device for the whole session; unset or empty keeps the default desktop context."""

import os

import pytest
from playwright.sync_api import Playwright

E2E_DEVICE = os.environ.get("E2E_DEVICE", "")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, playwright: Playwright) -> dict:
    if not E2E_DEVICE:
        return browser_context_args
    device = {k: v for k, v in playwright.devices[E2E_DEVICE].items() if k != "default_browser_type"}
    return {**browser_context_args, **device}
