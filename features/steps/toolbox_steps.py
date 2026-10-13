# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Toolbox outage steps: the development outage switch, the retry beat tasks run now, draft status and alerts."""

from __future__ import annotations

import time

from behave import given, then, when

COMMUNICATOR_ADMIN = "api/communicator/v2/admin/default-europe/"
LEADS_ADMIN = "api/leads/v2/admin/default-europe/"
NOTIFICATIONS_ADMIN = "api/notifications/v2/admin/default-europe/"
POLL_TIMEOUT_S = 30


def set_outage(api, down: bool):
    """Also posted by `environment.after_scenario` for `@toolbox-down` — keep the URL in sync."""
    return api.post(api.url(f"{COMMUNICATOR_ADMIN}test/toolbox-outage/"), json={"down": down})


def _post_ok(context, path: str) -> None:
    context.response = context.api.post(context.api.url(path))
    assert context.response.status_code == 200, f"{path}: {context.response.status_code} {context.response.text[:300]}"
    context.response_data = context.response.json()


@given("the AI toolbox outage switch is on")
def step_outage_on(context):
    response = set_outage(context.api, True)
    assert response.status_code == 200, f"toolbox-outage: {response.status_code} {response.text[:300]}"
    assert response.json() == {"down": True}


@when("the AI toolbox outage switch is turned off")
def step_outage_off(context):
    response = set_outage(context.api, False)
    assert response.status_code == 200, f"toolbox-outage: {response.status_code} {response.text[:300]}"
    assert response.json() == {"down": False}


@when("the communicator retries failed drafts")
def step_retry_drafts(context):
    _post_ok(context, f"{COMMUNICATOR_ADMIN}test/retry-drafts/")


@when("leads retries failed intel analyses")
def step_retry_analyses(context):
    _post_ok(context, f"{LEADS_ADMIN}test/retry-analyses/")


@then("the retry recovered {recovered:d} and failed {failed:d}")
def step_retry_counts(context, recovered, failed):
    assert context.response_data == {"recovered": recovered, "failed": failed}, context.response_data


@then('the message "{alias}" has status "{status}"')
def step_message_status(context, alias, status):
    response = context.api.get(context.api.url(f"{COMMUNICATOR_ADMIN}review/{context.saved[alias]}/"))
    assert response.status_code == 200, f"review detail: {response.status_code} {response.text[:300]}"
    data = response.json()
    assert data["status"] == status, f"{data['status']} ({data['failure_code']}: {data['failure_detail']})"


@then('a notification titled "{title}" exists')
def step_notification_exists(context, title):
    url = context.api.url(f"{NOTIFICATIONS_ADMIN}notifications/?page_size=100")
    deadline = time.monotonic() + POLL_TIMEOUT_S
    while True:
        titles = [item["title"] for item in context.api.get(url).json()["results"]]
        if title in titles or time.monotonic() > deadline:
            break
        time.sleep(1)
    assert title in titles, f"{title!r} not in {titles}"
