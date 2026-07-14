# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import Any

import requests


def assert_status(response: requests.Response, expected: int) -> None:
    assert response.status_code == expected, (
        f"Expected status {expected}, got {response.status_code}: {response.text[:200]}"
    )


def assert_json_key(data: dict[str, Any], key: str) -> None:
    assert key in data, f"Key '{key}' not found in response. Keys: {list(data.keys())}"


def assert_count(items: list[Any], expected: int) -> None:
    assert len(items) == expected, f"Expected {expected} items, got {len(items)}"


def extract_items(response: requests.Response) -> list[dict[str, Any]]:
    """Extract items from Volkanos API response.

    Volkanos format: {"meta": {...}, "data": [...], "pagination": {...}}
    Also handles flat list or {"results": [...]} for future-proofing.
    """
    data = response.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
        if "results" in data:
            return data["results"]
    return data
