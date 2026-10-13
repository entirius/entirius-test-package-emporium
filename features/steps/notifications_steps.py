# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Notifications steps: drive the escalation clock and wait for the worker to finish deliveries."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from behave import then, when

NOTIFICATIONS_ADMIN = "api/notifications/v2/admin/default-europe/"
DELIVERY_TIMEOUT_S = 30


@when("I run the notifications escalation {minutes:d} minutes from now")
def step_run_escalation(context, minutes):
    now = (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()
    url = context.api.url(f"{NOTIFICATIONS_ADMIN}test/run-escalation/")
    context.response = context.api.post(url, json={"now": now})
    context.response_data = context.response.json()


@then('the notification results contain the title "{title}"')
def step_results_contain_title(context, title):
    titles = [item["title"] for item in context.response_data["results"]]
    assert title in titles, f"{title!r} not in {titles}"


@then('the notification "{alias}" has deliveries')
def step_notification_deliveries(context, alias):
    """Deliveries run on the worker — poll until every expected kind reaches its status."""
    expected = {row["kind"]: row["status"] for row in context.table}
    url = context.api.url(f"{NOTIFICATIONS_ADMIN}notifications/{context.saved[alias]}/")
    deadline = time.monotonic() + DELIVERY_TIMEOUT_S
    while True:
        actual = {d["kind"]: d["status"] for d in context.api.get(url).json()["deliveries"]}
        if actual == expected or time.monotonic() > deadline:
            break
        time.sleep(0.5)
    assert actual == expected, f"deliveries: expected {expected}, got {actual}"
