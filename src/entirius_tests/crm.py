# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared helpers of the CRM steps (`features/steps/crm_*.py`): admin API roots of leads, communicator and todo, a
status-checking JSON read and a poll."""

from __future__ import annotations

import time

from entirius_tests import clock

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


def staff_id(context, role: str) -> int:
    username = context.staff_users[role][0]
    users = ok(context.api.get(url(context, LEADS, "assignable-users/"), params={"search": username}))["results"]
    return next(user["id"] for user in users if user["username"] == username)


def send_due(context) -> None:
    """The send beat once, now; waits while the stack's own beat holds its lock."""
    ok(clock.run_beat_send_waiting(context.api, context.channel))
