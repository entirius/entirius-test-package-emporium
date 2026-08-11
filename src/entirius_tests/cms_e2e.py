# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared plumbing for the CMS e2e suite: env config and munin module gating."""

from __future__ import annotations

import os

import pytest
import requests

from entirius_tests.munin import MUNIN_REGISTRY_PATH, parse_modules

CMS_BASE_URL = os.environ.get("CMS_BASE_URL", "http://localhost:8180")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def module_installed(key: str) -> bool:
    """Munin registry probe; an unreachable backend or empty registry returns
    True so the test fails with its real error instead of a silent skip."""
    try:
        resp = requests.get(f"{API_BASE_URL}/{MUNIN_REGISTRY_PATH}", timeout=10)
        modules = parse_modules(resp.json())
        return True if modules is None else key in modules
    except Exception:  # noqa: BLE001
        return True


def require_module(key: str) -> pytest.MarkDecorator:
    """Module gate for a test module: `pytestmark = require_module("atlas")`."""
    return pytest.mark.skipif(
        not module_installed(key), reason=f"module '{key}' not installed (munin registry)"
    )
