# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Mail sandbox steps (GreenMail via `entirius_tests.mail`). Fixture mails live in `fixtures/mail/`.
Scenarios that need an empty mailbox say so in their own Background — seed purges once, scenarios
never rely on order."""

from __future__ import annotations

from pathlib import Path

from behave import given, then, when

from entirius_tests import mail


def _fixture_mail(context, name: str) -> Path:
    """`fixtures/mail/` sits next to `package/` (`context.test_package_path`'s parent)."""
    path = Path(context.test_package_path).parent / "fixtures" / "mail" / name
    assert path.is_file(), f"mail fixture not found: {path}"
    return path


def _last_message(context):
    messages = mail.list_messages()
    assert messages, "sandbox mailbox is empty"
    return mail.get_message(messages[-1]["uid"])


@given('the value "{value}" is saved as "{alias}"')
def step_save_literal(context, value, alias):
    """Stands in for an id a real flow would have saved (e.g. our outbound Message-ID)."""
    context.saved[alias] = value


@given("the sandbox mailbox is empty")
def step_mailbox_empty(context):
    mail.purge()
    assert mail.count() == 0, "sandbox mailbox not empty after purge"


@then("the sandbox mailbox contains {n:d} messages")
def step_mailbox_contains(context, n):
    actual = mail.wait_for_count(n)
    assert actual == n, f"expected {n} messages in the sandbox mailbox, found {actual}"


@when('I inject the fixture mail "{name}" into INBOX')
def step_inject_mail(context, name):
    mail.inject(_fixture_mail(context, name))


@when('I inject the fixture mail "{name}" into INBOX replying to "{alias}"')
def step_inject_mail_reply(context, name, alias):
    assert alias in context.saved, f"nothing saved as {alias!r}. Saved: {list(context.saved)}"
    mail.inject(_fixture_mail(context, name), message_id=str(context.saved[alias]))


@when('I send the fixture mail "{name}" over SMTP to the sandbox')
def step_send_mail(context, name):
    eml = mail.render_fixture(_fixture_mail(context, name))
    mail.send_raw(eml, sender="bdd-sender@example.test", recipients=[mail.SANDBOX_EMAIL])


@then('the last sandbox message has header "{header}" equal to "{value}"')
def step_last_message_header(context, header, value):
    actual = _last_message(context)[header]
    resolved = value
    for alias, saved in context.saved.items():
        resolved = resolved.replace(f"{{{alias}}}", str(saved))
    assert actual == resolved, f"header {header!r}: expected {resolved!r}, got {actual!r}"


@then('the last sandbox message subject starts with "{prefix}"')
def step_last_message_subject(context, prefix):
    subject = _last_message(context)["Subject"] or ""
    assert subject.startswith(prefix), f"subject {subject!r} does not start with {prefix!r}"
