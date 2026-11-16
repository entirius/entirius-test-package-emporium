# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared helpers of the CRM steps (`features/steps/crm_*.py`): admin API roots of leads, communicator and todo, a
status-checking JSON read and a poll."""

from __future__ import annotations

import time
from contextlib import contextmanager

from entirius_tests import clock
from entirius_tests.auth import obtain_jwt_token

LEADS = "api/leads/v2/admin/{channel}/"
COMMUNICATOR = "api/communicator/v2/admin/{channel}/"
TODO = "api/todo/v2/admin/{channel}/"
POLL_TIMEOUT_S = 60


def url(context, base: str, path: str = "") -> str:
    return context.api.url(base.format(channel=context.channel) + path)


def ok(response, expected: int = 200):
    if response.status_code != expected:
        raise AssertionError(f"{response.request.url} -> {response.status_code}: {response.text[:400]}")
    return response.json() if response.content else None


def poll(check, timeout: float = POLL_TIMEOUT_S):
    deadline = time.monotonic() + timeout
    while not (value := check()) and time.monotonic() < deadline:
        time.sleep(1)
    return value


@contextmanager
def as_role(context, role: str):
    """Requests as the staff user of `role` with their own token; the admin login comes back whatever happens."""
    username, password = context.staff_users[role]
    context.api.set_auth_token(obtain_jwt_token(context.api.base_url, username, password))
    try:
        yield
    finally:
        token = obtain_jwt_token(context.api.base_url, context.admin_username, context.admin_password)
        context.api.set_auth_token(token)


def staff_id(context, role: str) -> int:
    username = context.staff_users[role][0]
    users = ok(context.api.get(url(context, LEADS, "assignable-users/"), params={"search": username}))["results"]
    return next(user["id"] for user in users if user["username"] == username)


def send_due(context) -> None:
    """The send beat once, now; waits while the stack's own beat holds its lock."""
    ok(clock.run_beat_send_waiting(context.api, context.channel))


def referral_in_review(context, email: str) -> dict | None:
    """The newest review draft to `email` that is a referral request. The queue lists the oldest first and a long
    run leaves more than one page in it, so the pages are read from the last one back."""
    size = 100
    params = {"status": "review_required", "page_size": size}
    first = ok(context.api.get(url(context, COMMUNICATOR, "review/"), params=params))
    pages = max(1, -(-first["count"] // size))
    for page in range(pages, 0, -1):
        rows = (
            first["results"]
            if page == 1
            else ok(context.api.get(url(context, COMMUNICATOR, "review/"), params={**params, "page": page}))["results"]
        )
        for row in reversed(rows):
            if row.get("referral_request") is False:
                continue
            detail = ok(context.api.get(url(context, COMMUNICATOR, f"review/{row['id']}/")))
            if detail.get("referral_request") and detail["thread"]["recipient_email"] == email:
                return detail
    return None
