# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Communicator clock steps (development-only test endpoints via `entirius_tests.clock`).
Need `the channel is the primary channel` and an authenticated admin earlier in the scenario."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from behave import given, when

from entirius_tests import clock

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _next_weekday_at(weekday: str, hhmm: str, today: date | None = None) -> str:
    """ISO datetime of the next `weekday` (today included) at `hhmm`, naive — the channel's timezone applies."""
    start = today or date.today()
    offset = (WEEKDAYS.index(weekday.lower()) - start.weekday()) % 7
    return datetime.combine(start + timedelta(days=offset), time.fromisoformat(hhmm.zfill(5))).isoformat()


def _assert_ok(response) -> None:
    assert response.status_code in (200, 202, 204), f"{response.request.url} -> {response.status_code}: {response.text}"


@given("the channel clock is {weekday} {hhmm}")
def step_channel_clock(context, weekday, hhmm):
    _assert_ok(clock.set_channel_clock(context.api, context.channel, _next_weekday_at(weekday, hhmm)))


@when("the beat send task has run")
def step_beat_send(context):
    _assert_ok(clock.run_beat_send(context.api, context.channel))


@when("the IMAP poll task has run")
def step_imap_poll(context):
    _assert_ok(clock.run_imap_poll(context.api, context.channel))
