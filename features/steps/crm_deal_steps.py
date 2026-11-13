# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CRM deal steps: open a deal on a scenario's company, and the board totals compared before and after (the board
sums every deal of the channel, so a re-run on one database only ever checks what the scenario added)."""

from __future__ import annotations

from decimal import Decimal

from behave import given, then, when

from entirius_tests.crm import LEADS, ok, url


def open_deal(context, title: str, value: str, alias: str, currency: str | None) -> None:
    body = {"company_id": context.saved[alias], "title": title, "value_one_off": value}
    body |= {"currency": currency} if currency else {}
    context.response = context.api.post(url(context, LEADS, "deals/"), json=body)
    context.response_data = context.response.json()
    if context.response.status_code == 201:
        context.saved["deal"] = context.response_data["id"]


@given('a deal "{title}" worth "{value}" is opened on the company "{alias}"')
def step_deal_opened(context, title, value, alias):
    open_deal(context, title, value, alias, None)
    ok(context.response, 201)


@when('a deal "{title}" worth "{value}" is opened on the company "{alias}"')
def step_open_deal(context, title, value, alias):
    open_deal(context, title, value, alias, None)


@when('a deal "{title}" worth "{value}" is opened in "{currency}" on the company "{alias}"')
def step_open_deal_currency(context, title, value, currency, alias):
    open_deal(context, title, value, alias, currency)
    ok(context.response, 201)


def board(context) -> dict[str, dict]:
    columns = ok(context.api.get(url(context, LEADS, "deals/board/")))["results"]
    return {column["stage"]["key"]: column for column in columns}


def one_off(column: dict, currency: str) -> Decimal:
    return sum((Decimal(row["one_off"]) for row in column["totals"] if row["currency"] == currency), Decimal(0))


@given("the board totals are remembered")
def step_board_before(context):
    context.saved["board"] = board(context)


@then('the board total of the stage "{stage}" grew by "{first}" in "{first_code}" and "{second}" in "{second_code}"')
def step_board_totals(context, stage, first, first_code, second, second_code):
    before, after = context.saved["board"][stage], board(context)[stage]
    for value, code in ((first, first_code), (second, second_code)):
        grown = one_off(after, code) - one_off(before, code)
        assert grown == Decimal(value), f"{stage} {code} grew by {grown}, expected {value}: {after['totals']}"


@then('the board count of the stage "{stage}" grew by {count:d}')
def step_board_count(context, stage, count):
    grown = board(context)[stage]["count"] - context.saved["board"][stage]["count"]
    assert grown == count, f"{stage} count grew by {grown}"
