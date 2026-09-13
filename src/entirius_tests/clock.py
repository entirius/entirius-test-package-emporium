# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Communicator development-only test endpoints: move a channel's clock, run the beat send and the IMAP
poll on demand instead of waiting for cron. All live under `api/communicator/v2/admin/<channel_idx>/test/`
and answer 404 outside `ENVIRONMENT=development`. The caller authenticates the client as an admin first.
"""

from __future__ import annotations

import requests

from entirius_tests.api_client import ApiClient

COMMUNICATOR_TEST_PATH = "api/communicator/v2/admin/{channel_idx}/test/"
CLOCK_PATH = "clock/"
SEND_DUE_PATH = "send-due/"
POLL_NOW_PATH = "poll-now/"


def _post(api: ApiClient, channel_idx: str, path: str, body: dict | None = None) -> requests.Response:
    url = api.url(COMMUNICATOR_TEST_PATH.format(channel_idx=channel_idx) + path)
    return api.post(url, json=body or {})


def set_channel_clock(api: ApiClient, channel_idx: str, iso_dt: str) -> requests.Response:
    return _post(api, channel_idx, CLOCK_PATH, {"iso_datetime": iso_dt})


def run_beat_send(api: ApiClient, channel_idx: str) -> requests.Response:
    return _post(api, channel_idx, SEND_DUE_PATH)


def run_imap_poll(api: ApiClient, channel_idx: str) -> requests.Response:
    return _post(api, channel_idx, POLL_NOW_PATH)
