# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Siteintel steps — only what the shared v2 admin steps lack: finish an audit through the development
run-now endpoint and read one source's report out of the audit detail it returns."""

from __future__ import annotations

import json
from datetime import datetime

from behave import given, then, when

SITEINTEL_ADMIN = "api/siteintel/v2/admin/default-europe/"
FAR_FUTURE = "2100-01-01T00:00:00Z"


def _report(context, source: str) -> dict:
    reports = {report["source"]: report for report in context.response_data.get("reports", [])}
    assert source in reports, f"no report for {source!r}; sources: {sorted(reports)}"
    return reports[source]


def _processed_field(report: dict, path: str):
    value = report["processed"]
    for key in path.split("."):
        assert isinstance(value, dict) and key in value, f"processed has no {path!r}: {report['processed']}"
        value = value[key]
    return value


def _json_or_text(text: str):
    """`0`, `true`, `null` compare as JSON values; anything else as the literal string."""
    try:
        return json.loads(text)
    except ValueError:
        return text


@given("no valid siteintel audit is cached")
def step_expire_all(context):
    response = context.api.post(context.api.url(f"{SITEINTEL_ADMIN}test/expire-now/"), json={"now": FAR_FUTURE})
    assert response.status_code == 200, f"expire-now: {response.status_code} {response.text[:300]}"


@when('the audit test run of "{alias}" has completed')
def step_run_now(context, alias):
    url = context.api.url(f"{SITEINTEL_ADMIN}test/run-now/{context.saved[alias]}/")
    context.response = context.api.post(url, json={})
    assert context.response.status_code == 200, f"run-now: {context.response.status_code} {context.response.text[:300]}"
    context.response_data = context.response.json()


@then('the report for source "{source}" should have status "{status}"')
def step_report_status(context, source, status):
    report = _report(context, source)
    assert report["status"] == status, f"{source}: {report['status']} ({report['error_code']} {report['error_detail']})"


@then('the report for source "{source}" should have processed field "{path}" set')
def step_report_processed_field(context, source, path):
    assert _processed_field(_report(context, source), path) is not None, f"{source}: {path} is null"


@then('the report for source "{source}" should have processed field "{path}" equal to "{expected}"')
def step_report_processed_field_equals(context, source, path, expected):
    actual = _processed_field(_report(context, source), path)
    wanted = _json_or_text(expected)
    assert actual == wanted, f"{source}: {path} = {actual!r}, expected {wanted!r}"


@then('I save the modified_at of the report for source "{source}" as "{alias}"')
def step_save_report_modified_at(context, source, alias):
    context.saved[alias] = _report(context, source)["modified_at"]


@then('the report for source "{source}" was modified after "{alias}"')
def step_report_modified_after(context, source, alias):
    before, after = context.saved[alias], _report(context, source)["modified_at"]
    assert datetime.fromisoformat(after) > datetime.fromisoformat(before), f"{source}: {after} is not after {before}"
