# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Leads steps — only what the shared v2 admin steps lack: a multipart CSV upload, polling an import batch,
a contact_forms submission with the channel's API key, and field checks on list items."""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from behave import then, when

# X-API-KEY values of fixtures/django_contact_forms.cfg.yaml (apikey pk 1 and 2).
CONTACT_FORM_API_KEYS = {"default-europe": "1" * 64, "default-local": "2" * 64}
IMPORT_TIMEOUT_S = 60


def _v2_url(context, path: str) -> str:
    """`leads/admin/{channel_idx}/x/` → `<base>/api/leads/v2/admin/<channel>/x/`, saved aliases resolved."""
    resolved = path.replace("{channel_idx}", context.channel or "")
    for key, value in (context.saved or {}).items():
        resolved = resolved.replace(f"{{{key}}}", str(value))
    module, _, rest = resolved.partition("/")
    return context.api.url(f"api/{module}/v2/{rest}")


def _results(context) -> list[dict]:
    data = context.response_data
    return data.get("results", []) if isinstance(data, dict) else data


@when('I upload the package file "{name}" to the v2 admin endpoint "{path}"')
def step_upload_package_file(context, name, path):
    url = _v2_url(context, path)
    file_path = Path(context.test_package_path) / name
    with file_path.open("rb") as handle:
        context.response = context.api.post(url, files={"file": (name, handle, "text/csv")})
    context.response_data = context.response.json()


@then('the import batch "{alias}" has finished')
def step_import_batch_finished(context, alias):
    url = _v2_url(context, f"leads/admin/{{channel_idx}}/imports/{context.saved[alias]}/")
    deadline = time.monotonic() + IMPORT_TIMEOUT_S
    while True:
        context.response = context.api.get(url)
        context.response_data = context.response.json()
        if context.response_data.get("status") in ("done", "failed") or time.monotonic() > deadline:
            break
        time.sleep(1)
    assert context.response_data.get("status") == "done", f"import batch: {context.response_data}"


@when('I submit a contact form on channel "{idx}" with body')
def step_submit_contact_form(context, idx):
    url = context.api.url(f"api/contact-forms/v2/{idx}/submit/")
    headers = {"X-API-KEY": CONTACT_FORM_API_KEYS[idx]}
    context.response = requests.post(url, json=json.loads(context.text), headers=headers, timeout=30)
    assert context.response.status_code == 201, f"submit: {context.response.status_code} {context.response.text[:300]}"


@then('the import report row {row:d} should have action "{action}"')
def step_report_row_action(context, row, action):
    entries = [entry for entry in context.response_data["report"] if entry["row"] == row]
    assert entries and entries[0]["action"] == action, f"row {row}: {entries}"


@then('the import report should contain the reason "{reason}"')
def step_report_reason(context, reason):
    reasons = {entry["reason"] for entry in context.response_data["report"]}
    assert reason in reasons, f"reasons: {sorted(reasons)}"


@then('the result with "{key}" equal to "{value}" should have a null "{field}"')
def step_result_field_null(context, key, value, field):
    items = [item for item in _results(context) if str(item.get(key)) == value]
    assert items, f"no result with {key}={value}"
    assert items[0][field] is None, f"{field}: {items[0][field]!r}"
