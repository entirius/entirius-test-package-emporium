# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Plumbing for the AI studio CMS e2e (`e2e/cms/test_ai_studio_*.py`): the enrichment admin API (setup and reset),
the AI toolbox tracker usage records (call counts) and the screenshot gallery for the operator.

The stack talks to a toolbox that serves only `fake` models, so every AI answer is a deterministic placeholder.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests
from playwright.sync_api import Locator, Page

from entirius_tests.auth import obtain_jwt_token
from entirius_tests.cms_e2e import ADMIN_PASSWORD, ADMIN_USERNAME, API_BASE_URL

CHANNEL = os.environ.get("E2E_CHANNEL", "default-europe")
ENRICHMENT = "api/enrichment/v2/admin"
PIM = f"api/pim/v2/admin/{CHANNEL}"
TOOLBOX_URL = os.environ.get("TOOLBOX_URL", "http://localhost:8010")
TOOLBOX_CHANNEL = os.environ.get("AI_TOOLBOX_CHANNEL", "zeno-test")
TOOLBOX_USERNAME = os.environ.get("TOOLBOX_USERNAME", "admin")
TOOLBOX_PASSWORD = os.environ.get("TOOLBOX_PASSWORD", "admin")
# The zeno root holds the gallery: <zeno>/repos/tests/<this package>/src/entirius_tests/ai_studio_e2e.py.
_ZENO_ROOT = Path(__file__).resolve().parents[5]
SCREENSHOT_DIR = Path(os.environ.get("E2E_SCREENSHOT_DIR", _ZENO_ROOT / ".playwright-mcp" / "ai-studio"))
SCREEN_SIZES = {"desktop": (1280, 800), "phone": (390, 844)}
TRACKER_PAGES = 5
_HTTP_TIMEOUT = 30


class AdminApi:
    """JWT session against one API (the service, or the toolbox for its tracker)."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        token = obtain_jwt_token(self.base_url, username, password)
        self.session.headers["Authorization"] = f"Bearer {token}"

    def call(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(method, f"{self.base_url}/{path.lstrip('/')}", timeout=_HTTP_TIMEOUT, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def get(self, path: str, **params: Any) -> Any:
        return self.call("GET", path, params=params)

    def post(self, path: str, body: dict | None = None) -> Any:
        return self.call("POST", path, json=body or {})


def service_api() -> AdminApi:
    return AdminApi(API_BASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD)


def toolbox_api() -> AdminApi:
    return AdminApi(TOOLBOX_URL, TOOLBOX_USERNAME, TOOLBOX_PASSWORD)


def wait_for(check: Callable[[], Any], *, timeout: float = 60, every: float = 1.0) -> Any:
    """Poll `check` until it returns something truthy; the last value is returned, falsy after the timeout."""
    deadline = time.monotonic() + timeout
    while not (value := check()) and time.monotonic() < deadline:
        time.sleep(every)
    return value


# --- enrichment ----------------------------------------------------------------------------------------------------


def pending_proposals(api: AdminApi, sku: str) -> list[dict]:
    query = {"subject_ref": sku, "target_module": "pim", "status": "pending", "page_size": 200}
    return api.get(f"{ENRICHMENT}/proposals/", **query)["results"]


def reject_pending(api: AdminApi, sku: str) -> None:
    """Start a product from a clean drawer: reject what an earlier run left to review."""
    for proposal in pending_proposals(api, sku):
        api.post(f"{ENRICHMENT}/proposals/{proposal['id']}/reject/", {"reason": "e2e reset"})


def task_proposals(api: AdminApi, task_id: int) -> list[dict]:
    return api.get(f"{ENRICHMENT}/proposals/", task=task_id, status="pending", page_size=200)["results"]


def latest_task_id(api: AdminApi, sku: str) -> int:
    """Id of the newest list task of `sku` (0 when none)."""
    tasks = api.get(f"{ENRICHMENT}/tasks/", subject_ref=sku, target_module="pim", page_size=1)["results"]
    return tasks[0]["id"] if tasks else 0


def task(api: AdminApi, task_id: int) -> dict:
    return api.get(f"{ENRICHMENT}/tasks/{task_id}/")


def wait_task_finished(api: AdminApi, task_id: int, timeout: float = 90) -> dict:
    """The task once it left `open` / `in_progress`."""
    finished = wait_for(lambda: _finished(task(api, task_id)), timeout=timeout)
    if not finished:
        raise TimeoutError(f"task {task_id} did not finish within {timeout} s")
    return finished


def _finished(found: dict) -> dict | None:
    return found if found["status"] not in ("open", "in_progress") else None


def channel_languages() -> list[str]:
    return service_api().get(f"{ENRICHMENT}/languages/", target_module="pim", channel=CHANNEL)


def revisions(api: AdminApi, proposal_id: int) -> list[dict]:
    return api.get(f"{ENRICHMENT}/proposals/{proposal_id}/revisions/")


def delete_templates(api: AdminApi, prefix: str) -> None:
    """Drop the templates an earlier run of a test created (keys start with `prefix`)."""
    for template in api.get(f"{ENRICHMENT}/templates/"):
        if template["key"].startswith(prefix):
            api.call("DELETE", f"{ENRICHMENT}/templates/{template['key']}/")


def profile(api: AdminApi, channel: str = "") -> dict:
    """A profile scope (`version`, `data`): the whole company, or a channel overlay."""
    return api.get(f"{ENRICHMENT}/profile/", channel=channel)


def put_profile(api: AdminApi, data: dict, note: str, channel: str = "") -> dict:
    return api.call("PUT", f"{ENRICHMENT}/profile/", params={"channel": channel}, json={"data": data, "note": note})


def product(sku: str) -> dict:
    return service_api().get(f"{PIM}/products/{sku}/")


def patch_product(sku: str, body: dict) -> None:
    service_api().call("PATCH", f"{PIM}/products/{sku}/", json=body)


# --- toolbox -------------------------------------------------------------------------------------------------------


def tracker_records(api: AdminApi, *, tool_name: str = "completion") -> list[dict]:
    """The newest usage records of the toolbox channel (newest first, at most `TRACKER_PAGES` pages)."""
    path = f"api/ai-tracker/v2/admin/{TOOLBOX_CHANNEL}/usage/records/"
    found: list[dict] = []
    for page in range(1, TRACKER_PAGES + 1):
        body = api.get(path, tool_name=tool_name, page=page, page_size=100)
        found += body["results"]
        if not body.get("next"):
            break
    return found


def task_calls(api: AdminApi, task_id: int, selector: str = "") -> list[dict]:
    """Completion records tagged `task:<id>` (and, when given, whose selector tag starts with `selector`)."""
    return [
        record
        for record in tracker_records(api)
        if f"task:{task_id}" in _tags(record) and _tags(record)[0].startswith(selector)
    ]


def _tags(record: dict) -> list[str]:
    return (record.get("metadata") or {}).get("tags") or [""]


def toolbox_has_seo() -> bool:
    """The toolbox serves the SEO app (`/api/ai-seo/`) — the local image gets it only after a rebuild.

    Only a reachable toolbox whose schema lacks the app is "no SEO": a toolbox that is down or answers an error
    raises, so the test fails with its real error instead of a silent skip."""
    resp = requests.get(f"{TOOLBOX_URL}/api/schema/", params={"format": "json"}, timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()
    return any("/api/ai-seo/" in path for path in resp.json().get("paths", {}))


# --- gallery -------------------------------------------------------------------------------------------------------


def shoot(page: Page, name: str, focus: Locator | None = None) -> None:
    """`<name>-desktop.png` (1280 × 800) and `<name>-phone.png` (390 × 844), `focus` scrolled into view; then back to
    the desktop viewport."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for label, (width, height) in SCREEN_SIZES.items():
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(300)  # let the layout settle after the resize
        if focus is not None:
            focus.scroll_into_view_if_needed()
        page.screenshot(path=str(SCREENSHOT_DIR / f"{name}-{label}.png"))
    page.set_viewport_size({"width": SCREEN_SIZES["desktop"][0], "height": SCREEN_SIZES["desktop"][1]})
