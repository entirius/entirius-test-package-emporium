# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for delivery points BDD tests.

Cleanup helpers that find resources by code (since URLs use integer PKs)
and delete them idempotently.
"""

from __future__ import annotations

from behave import given


@given('I ensure delivery type with code "{code}" is cleaned up')
def step_ensure_type_cleaned(context, code):
    """Find delivery type by code via list endpoint, delete if exists."""
    url = context.api.url("api/deliverypoints/v2/admin/types/")
    resp = context.api.get(url, params={"page_size": 100})
    if resp.status_code != 200:
        return
    for item in resp.json().get("results", []):
        if item["code"] == code:
            del_url = context.api.url(f"api/deliverypoints/v2/admin/types/{item['id']}/")
            context.api.delete(del_url)
            return


@given('I ensure delivery point with code "{code}" is cleaned up')
def step_ensure_point_cleaned(context, code):
    """Find delivery point by code via list endpoint, delete if exists."""
    url = context.api.url("api/deliverypoints/v2/admin/points/")
    resp = context.api.get(url, params={"search": code, "page_size": 100})
    if resp.status_code != 200:
        return
    for item in resp.json().get("results", []):
        if item["code"] == code:
            del_url = context.api.url(f"api/deliverypoints/v2/admin/points/{item['id']}/")
            context.api.delete(del_url)
            return
