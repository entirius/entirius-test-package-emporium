# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Step definitions for agreements-specific operations."""

from __future__ import annotations

from behave import given


@given('I ensure agreements definition "{slug}" is cleaned up')
def step_ensure_agreement_cleaned(context, slug):
    """Ensure a definition slug is available for creation.

    Since agreements admin API soft-deletes (is_active=False, slug remains),
    we can't truly remove it. Instead, if the definition exists, we hard-delete
    it via the API. If the API doesn't support hard-delete, we just accept
    that creating with this slug may need a PATCH instead of POST.

    Strategy: DELETE (soft), then PATCH is_active back for later re-deletion.
    The CRUD test should use PATCH to reset state if definition already exists.
    """
    url = context.api.url(f"api/agreements/v2/admin/definitions/{slug}/")
    # Just try to delete — accept any result
    context.api.delete(url)
