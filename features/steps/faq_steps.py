# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for FAQ BDD tests.

Cleanup helpers that find resources by their natural identifiers
(idx for groups, url_key for items) and delete them idempotently.
Items use integer PKs in detail URLs so cleanup must look up the PK first.
"""

from __future__ import annotations

from behave import given


@given('I ensure faq group with idx "{idx}" is cleaned up')
def step_ensure_faq_group_cleaned(context, idx):
    """Find FAQ group by idx via detail endpoint, delete if exists.

    Groups use idx as the URL identifier — a direct DELETE is sufficient.
    Accepts 204 (deleted) or 404 (already gone).
    """
    channel = context.channel or "default-europe"
    url = context.api.url(f"api/faq/v2/admin/{channel}/groups/{idx}/")
    resp = context.api.delete(url)
    # 204 = deleted, 404 = never existed, 405 = method not allowed (ignore)
    if resp.status_code not in (204, 404, 405):
        # Best-effort — do not block the test if cleanup fails
        return


@given('I ensure faq item with url_key "{url_key}" is cleaned up')
def step_ensure_faq_item_cleaned(context, url_key):
    """Find FAQ item by url_key via list search, then delete by integer PK.

    Items use integer PKs in detail URLs, so we must list-search first.
    """
    channel = context.channel or "default-europe"
    list_url = context.api.url(f"api/faq/v2/admin/{channel}/items/")
    resp = context.api.get(list_url, params={"search": url_key, "page_size": 100})
    if resp.status_code != 200:
        return
    for item in resp.json().get("results", []):
        if item.get("url_key") == url_key:
            del_url = context.api.url(f"api/faq/v2/admin/{channel}/items/{item['id']}/")
            context.api.delete(del_url)
            return
