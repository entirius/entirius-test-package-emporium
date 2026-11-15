# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CRM potential steps (U2): the dot of a scenario's company, the list filter, the manual colour, the thresholds put
back, and the rules of a later day asked of the service (`potential_service.compute` with `today` moved, read only)."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

from behave import given, then, when

from entirius_tests.crm import COMMUNICATOR, LEADS, ok, poll, url
from entirius_tests.stock_alerts import service_shell

COMPUTE = """
import datetime, json
from django.utils import timezone
from django_leads.models import Company
from django_leads.services import potential_service
company = Company.objects.select_related("channel").get(pk={pk})
verdict = potential_service.compute(company, today=timezone.localdate() + datetime.timedelta(days={days}))
print("VERDICT", json.dumps([str(verdict.colour), verdict.reason]))
"""


def company(context, alias: str) -> dict:
    return ok(context.api.get(url(context, LEADS, f"companies/{context.saved[alias]}/")))


def potential_url(context, alias: str) -> str:
    return url(context, LEADS, f"companies/{context.saved[alias]}/potential/")


def answer(context, response) -> None:
    context.response = response
    try:
        context.response_data = response.json()
    except ValueError:
        context.response_data = {}


@then('the company "{alias}" has no potential dot')
def step_no_dot(context, alias):
    found = company(context, alias)
    assert found["potential"] == "", f"potential: {found['potential']!r} ({found['potential_reason']})"


@then('the company "{alias}" has the potential "{colour}" because "{reason}"')
def step_potential(context, alias, colour, reason):
    found = company(context, alias)
    actual = (found["potential"], found["potential_reason"])
    assert actual == (colour, reason), f"potential {actual}, expected {(colour, reason)}"


@then('the company "{alias}" gets the potential "{colour}" because "{reason}"')
def step_potential_eventually(context, alias, colour, reason):
    """A threshold change recomputes the channel in the worker."""
    found = poll(
        lambda: (row := company(context, alias)) and (row["potential"], row["potential_reason"]) == (colour, reason)
    )
    last = company(context, alias)
    assert found, f"potential {(last['potential'], last['potential_reason'])}, expected {(colour, reason)}"


@then('the company "{alias}" has the potential "{colour}" set by hand with the reason "{reason}"')
def step_manual(context, alias, colour, reason):
    found = company(context, alias)
    actual = (found["potential"], found["potential_manual"], found["potential_comment"])
    assert actual == (colour, True, reason), f"potential {actual}"


@then('the company "{alias}" comes back in {days:d} days')
def step_back_in(context, alias, days):
    back = company(context, alias)["potential_return_on"]
    expected = date.today() + timedelta(days=days)
    assert back and abs((date.fromisoformat(back) - expected).days) <= 1, f"come-back day {back}, expected ~{expected}"


@then('the company "{alias}" comes back on "{day}"')
def step_back_on(context, alias, day):
    back = company(context, alias)["potential_return_on"]
    assert back == day, f"come-back day {back}, expected {day}"


@then('the company "{alias}" has no come-back day')
def step_no_back(context, alias):
    back = company(context, alias)["potential_return_on"]
    assert back is None, f"come-back day {back}"


@then('the company "{alias}" is in the list filtered by the potential "{value}"')
def step_in_filter(context, alias, value):
    params = {"potential": value, "search": context.saved[f"{alias}.domain"]}
    rows = ok(context.api.get(url(context, LEADS, "companies/"), params=params))["results"]
    assert [row["id"] for row in rows] == [context.saved[alias]], f"filter {value}: {rows}"


@then('in {days:d} days the service gives the company "{alias}" the potential "{colour}" because "{reason}"')
def step_later_day(context, days, alias, colour, reason):
    out = service_shell(COMPUTE.replace("{pk}", str(context.saved[alias])).replace("{days}", str(days)))
    found = re.search(r"VERDICT (.+)", out)
    assert found, f"no verdict: {out[-300:]}"
    assert json.loads(found.group(1)) == [colour, reason], f"in {days} days: {found.group(1)}"


@when('the draft of the company "{alias}" is skipped')
def step_skip_draft(context, alias):
    message_id = context.saved[f"{alias}.message"]
    ok(context.api.post(url(context, COMMUNICATOR, f"review/{message_id}/skip/"), json={"reason": "BDD later"}))


@given('the potential of the company "{alias}" is set to "{colour}" with the reason "{reason}"')
def step_manual_set(context, alias, colour, reason):
    step_manual_post(context, alias, colour, reason)
    ok(context.response)


@when('the potential of the company "{alias}" is set to "{colour}" with the reason "{reason}"')
def step_manual_post(context, alias, colour, reason):
    answer(context, context.api.post(potential_url(context, alias), json={"colour": colour, "comment": reason}))


@when('the potential of the company "{alias}" is set to "{colour}" without a reason')
def step_manual_blank(context, alias, colour):
    answer(context, context.api.post(potential_url(context, alias), json={"colour": colour, "comment": "  "}))


@when('the potential of the company "{alias}" goes back to automatic')
def step_manual_reset(context, alias):
    answer(context, context.api.delete(potential_url(context, alias)))


def put_back(context, potential: dict) -> None:
    ok(context.api.patch(url(context, LEADS, "channel/"), json={"potential": potential}))


@given("the potential thresholds are put back when the scenario ends")
def step_thresholds_back(context):
    """The channel's stored values are not readable apart from the defaults: the effective ones are written back."""
    current = ok(context.api.get(url(context, LEADS, "channel/")))["potential"]
    context.add_cleanup(put_back, context, current)
