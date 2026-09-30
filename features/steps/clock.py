# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Communicator clock steps (development-only test endpoints via `entirius_tests.clock`).
Need `the channel is the primary channel` and an authenticated admin earlier in the scenario."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from behave import given, when

from entirius_tests import clock


def _reference_weekday_at(weekday: str, hhmm: str) -> str:
    """ISO datetime of `weekday` of the holiday-free reference week at `hhmm`, naive — the channel timezone applies.

    Never counted from today: a real week with a PL holiday would close the channel and fail the scenarios."""
    return datetime.combine(clock.reference_day(weekday), time.fromisoformat(hhmm.zfill(5))).isoformat()


def _assert_ok(response) -> None:
    assert response.status_code in (200, 202, 204), f"{response.request.url} -> {response.status_code}: {response.text}"


def _set_clock(context, iso_dt: str) -> None:
    """The channel clock is cleared again when the scenario ends, so later features run on real time."""
    if getattr(context, "channel_clock", None) is None:
        context.add_cleanup(clock.clear_channel_clock, context.api, context.channel)
    _assert_ok(clock.set_channel_clock(context.api, context.channel, iso_dt))
    context.channel_clock = datetime.fromisoformat(iso_dt)


@given("the channel clock is {weekday} {hhmm}")
def step_channel_clock(context, weekday, hhmm):
    _set_clock(context, _reference_weekday_at(weekday, hhmm))


@when("the channel clock moves {days:d} days forward")
def step_channel_clock_forward(context, days):
    assert getattr(context, "channel_clock", None), "set the channel clock first"
    _set_clock(context, (context.channel_clock + timedelta(days=days)).isoformat())


@given("the send counters of the reference week are cleared")
def step_reset_counters(context):
    """The Redis day counters survive `make seed`; clearing them keeps the cap scenarios green on every re-run."""
    _assert_ok(clock.reset_send_counters(context.api, context.channel, clock.reference_week()))


@when("the beat send task has run")
def step_beat_send(context):
    """Both beat tasks run in-process; the counts are kept as the response."""
    context.response = clock.run_beat_send(context.api, context.channel)
    _assert_ok(context.response)
    context.response_data = context.response.json()


@when("the IMAP poll task has run")
def step_imap_poll(context):
    _assert_ok(clock.run_imap_poll(context.api, context.channel))
