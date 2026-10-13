# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Communicator development-only test endpoints: move a channel's clock, run the beat send and the IMAP
poll on demand instead of waiting for cron, clear the daily send counters. All live under
`api/communicator/v2/admin/<channel_idx>/test/` and answer 404 outside `ENVIRONMENT=development`. The caller
authenticates the client as an admin first.
"""

from __future__ import annotations

from datetime import date, timedelta

import requests

from entirius_tests.api_client import ApiClient

COMMUNICATOR_TEST_PATH = "api/communicator/v2/admin/{channel_idx}/test/"
CLOCK_PATH = "clock/"
SEND_DUE_PATH = "send-due/"
POLL_NOW_PATH = "poll-now/"
RESET_COUNTERS_PATH = "reset-counters/"

# Every channel clock step lands in this fixed ISO week, never in the real one: Monday 2026-09-21 to Sunday
# 2026-09-27 has no PL public holiday, and the next Monday (a C-16 next slot) is a business day too.
REFERENCE_MONDAY = date(2026, 9, 21)
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def reference_day(weekday: str) -> date:
    return REFERENCE_MONDAY + timedelta(days=WEEKDAYS.index(weekday.lower()))


def reference_week() -> list[date]:
    return [REFERENCE_MONDAY + timedelta(days=offset) for offset in range(7)]


def _post(api: ApiClient, channel_idx: str, path: str, body: dict | None = None) -> requests.Response:
    url = api.url(COMMUNICATOR_TEST_PATH.format(channel_idx=channel_idx) + path)
    return api.post(url, json={} if body is None else body)


def set_channel_clock(api: ApiClient, channel_idx: str, iso_dt: str) -> requests.Response:
    return _post(api, channel_idx, CLOCK_PATH, {"iso_datetime": iso_dt})


def clear_channel_clock(api: ApiClient, channel_idx: str) -> requests.Response:
    return _post(api, channel_idx, CLOCK_PATH, {"iso_datetime": None})


def run_beat_send(api: ApiClient, channel_idx: str) -> requests.Response:
    return _post(api, channel_idx, SEND_DUE_PATH)


def run_imap_poll(api: ApiClient, channel_idx: str) -> requests.Response:
    return _post(api, channel_idx, POLL_NOW_PATH)


def reset_send_counters(api: ApiClient, channel_idx: str, days: list[date]) -> requests.Response:
    return _post(api, channel_idx, RESET_COUNTERS_PATH, {"days": [day.isoformat() for day in days]})
