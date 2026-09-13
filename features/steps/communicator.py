# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Communicator steps: request a message through the development endpoint and inspect review responses."""

from __future__ import annotations

import json
import time

from behave import then, when

COMMUNICATOR_ADMIN = "api/communicator/v2/admin/default-europe/"
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."
CONTEXT = {
    "company_name": "Example Shop 1",
    "website": "example-shop-1.test",
    "hooks": "mobile performance 2/10; 40 third-party scripts",
    "last_name": "Kowalski",
}


def _field(data: dict, path: str):
    """Dotted lookup: `template.version_id`."""
    for part in path.split("."):
        assert isinstance(data, dict) and part in data, f"{path!r} missing in response"
        data = data[part]
    return data


def _store(context, response) -> None:
    context.response = response
    context.response_data = response.json() if response.content else {}


@when('I request the "{template_key}" message for "{email}" about "{subject_ref}"')
def step_communicate(context, template_key, email, subject_ref):
    _communicate(context, template_key, email, subject_ref, requires_review=True)


@when('I request the "{template_key}" message for "{email}" about "{subject_ref}" without review')
def step_communicate_without_review(context, template_key, email, subject_ref):
    _communicate(context, template_key, email, subject_ref, requires_review=False)


def _communicate(context, template_key, email, subject_ref, *, requires_review):
    recipient = {
        "email": email,
        "first_name": "Jan",
        "last_name": "Kowalski",
        "language": "pl",
        "legal_footer": LEGAL_FOOTER,
    }
    body = {
        "template_key": template_key,
        "recipient": recipient,
        "context": CONTEXT,
        "subject_ref": subject_ref,
        "requires_review": requires_review,
    }
    _store(context, context.api.post(context.api.url(f"{COMMUNICATOR_ADMIN}test/communicate/"), json=body))
    assert context.response.status_code == 201, f"communicate: {context.response.status_code} {context.response.text}"


def _review(context, alias: str, action: str, body: dict) -> None:
    url = context.api.url(f"{COMMUNICATOR_ADMIN}review/{context.saved[alias]}/{action}/")
    _store(context, context.api.post(url, json=body))


@when('I accept the message "{alias}"')
def step_accept(context, alias):
    _review(context, alias, "accept", {})


@when('I rewrite the message "{alias}" with body')
def step_rewrite(context, alias):
    _review(context, alias, "rewrite", json.loads(context.text))


@when('I edit the message "{alias}" with body')
def step_edit(context, alias):
    _review(context, alias, "edit", json.loads(context.text))


@when('I append a unique sentence to the body of template "{alias}"')
def step_edit_template(context, alias):
    """The original body is put back when the scenario ends, so re-runs on one seed do not accumulate."""
    url = context.api.url(f"{COMMUNICATOR_ADMIN}templates/{context.saved[alias]}/")
    template = context.api.get(url).json()
    fields = (
        "key",
        "kind",
        "language",
        "subject",
        "body",
        "json_schema",
        "model",
        "requires_legal_footer",
        "auto_approve",
        "is_active",
    )
    body = {name: template[name] for name in fields}
    context.add_cleanup(context.api.put, url, json=dict(body))
    body["body"] = f"{template['body']}\nBDD C-29 revision {time.time_ns()}."
    _store(context, context.api.put(url, json=body))


@then('I save the template id of "{template_key}" as "{alias}"')
def step_save_template_id(context, template_key, alias):
    templates = context.api.get(context.api.url(f"{COMMUNICATOR_ADMIN}templates/")).json()["results"]
    matches = [t["id"] for t in templates if t["key"] == template_key and t["language"] == "pl"]
    assert matches, f"template {template_key!r} not seeded"
    context.saved[alias] = matches[0]


@then('I save the nested response field "{path}" as "{alias}"')
def step_save_nested(context, path, alias):
    context.saved[alias] = _field(context.response_data, path)


@then('the nested response field "{path}" should equal "{expected}"')
def step_nested_equals(context, path, expected):
    for key, value in context.saved.items():
        expected = expected.replace(f"{{{key}}}", str(value))
    actual = str(_field(context.response_data, path))
    assert actual == expected, f"{path}: expected {expected!r}, got {actual!r}"


@then('the nested response field "{path}" should not equal "{unexpected}"')
def step_nested_not_equals(context, path, unexpected):
    for key, value in context.saved.items():
        unexpected = unexpected.replace(f"{{{key}}}", str(value))
    assert str(_field(context.response_data, path)) != unexpected, f"{path} still {unexpected!r}"


@then('the response field "{field}" should not be empty')
def step_field_not_empty(context, field):
    assert _field(context.response_data, field), f"{field} is empty: {context.response_data.get(field)!r}"


@then('the response field "{field}" should be empty')
def step_field_empty(context, field):
    assert not _field(context.response_data, field), f"{field} is not empty: {context.response_data.get(field)!r}"


@then('the response field "{field}" should contain "{text}"')
def step_field_contains(context, field, text):
    assert text in str(_field(context.response_data, field)), f"{text!r} not in {field}"


@then('the message "{alias}" in the "{status}" queue uses template version "{version_alias}"')
def step_queue_message_version(context, alias, status, version_alias):
    url = context.api.url(f"{COMMUNICATOR_ADMIN}review/?status={status}&page_size=100")
    while url:
        page = context.api.get(url).json()
        found = [m for m in page["results"] if m["id"] == context.saved[alias]]
        if found:
            assert found[0]["template"]["version_id"] == context.saved[version_alias]
            return
        url = page["next"]
    raise AssertionError(f"message {context.saved[alias]} not in the {status} queue")
