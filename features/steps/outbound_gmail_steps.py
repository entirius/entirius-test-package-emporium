# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps of the Gmail API scenarios (communicator mail accounts, `gmail_api` sender routes, replies through the API).

The Gmail API test double (`tests/gmail_stub.py` of the communicator) is the only "Google" in these scenarios; its control
endpoints are reached at GMAIL_STUB_URL. The browser part of the OAuth flow is played by plain HTTP: open the consent URL
at the double, follow its redirect into the communicator's callback."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from behave import given, then, when

ADMIN = "api/communicator/v2/admin/{channel}/"
STUB = os.environ.get("GMAIL_STUB_URL", "http://localhost:8199").rstrip("/")
LEGAL_FOOTER = "Administrator danych: Example Seller sp. z o.o., ul. Testowa 1, Warszawa."
SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def _url(context, path: str = "") -> str:
    return context.api.url(ADMIN.format(channel=context.channel) + path)


def _ok(response, expected: int = 200):
    assert response.status_code == expected, f"{response.request.url} -> {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


def _stub(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(  # noqa: S310
        STUB + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - the local test double
        return json.loads(response.read() or b"{}")


def _account(context, alias: str) -> dict:
    return _ok(context.api.get(_url(context, f"accounts/{context.saved[f'{alias}_account_id']}/")))


def _sent_by(context, alias: str) -> list[dict]:
    return _stub("GET", f"/__stub/sent?email={context.saved[f'{alias}_email']}")["sent"]


def _parse(raw: str):
    import email
    from email import policy

    return email.message_from_string(raw, policy=policy.default)


def _remove_route(context, key: str) -> None:
    context.api.delete(_url(context, f"routes/{key}/"))


def _remove_account(context, account_id: int) -> None:
    context.api.delete(_url(context, f"accounts/{account_id}/"))


def _create_account(context, alias: str, inbound: bool) -> None:
    address = f"bdd-gmail-{alias}-{time.time_ns()}@ecom.example.test"
    data = _ok(context.api.post(_url(context, "accounts/"), json={"email": address, "inbound_enabled": inbound}), 201)
    context.saved[f"{alias}_account_id"], context.saved[f"{alias}_email"] = data["id"], address
    context.add_cleanup(_remove_account, context, data["id"])


@given("the gmail test double is reset")
def step_reset(context):
    _stub("POST", "/__stub/reset", {})


@given('a gmail account "{alias}" exists')
def step_account(context, alias):
    _create_account(context, alias, inbound=False)


@given('a gmail account "{alias}" exists that also reads replies')
def step_account_reads(context, alias):
    _create_account(context, alias, inbound=True)


@given('the gmail account "{alias}" is "{state}"')
@then('the gmail account "{alias}" is "{state}"')
def step_state(context, alias, state):
    assert _account(context, alias)["state"] == state, _account(context, alias)


@given('I connect the gmail account "{alias}" at the test double')
@when('I connect the gmail account "{alias}" at the test double')
def step_connect(context, alias):
    """Start (admin API), then the browser: consent page of the double, redirect to the callback."""
    start = _ok(context.api.post(_url(context, f"accounts/{context.saved[f'{alias}_account_id']}/connect/")))
    request = urllib.request.Request(start["authorization_url"])  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=15) as page:  # noqa: S310 - follows the redirect into the callback
            assert page.status == 200, page.status
            assert b"is connected" in page.read()
    except urllib.error.HTTPError as error:  # a refused sign-in shows its reason
        raise AssertionError(f"callback answered {error.code}: {error.read()[:300]!r}") from None


@then('the test double saw an offline consent request with PKCE for "{alias}" asking only for the send permission')
def step_consent(context, alias):
    auth = _stub("GET", "/__stub/last_auth")
    assert (auth["access_type"], auth["prompt"], auth["code_challenge_method"]) == ("offline", "consent", "S256"), auth
    assert auth["login_hint"] == context.saved[f"{alias}_email"] and auth["state"], auth
    assert set(auth["scope"].split()) == {"openid", "email", SEND_SCOPE}, auth["scope"]


@then("no gmail account answer contains a token")
def step_no_token(context):
    text = context.api.get(_url(context, "accounts/")).text + json.dumps(_account(context, "gm1"))
    assert "rt-" not in text and "at-" not in text and "refresh" not in text.lower(), (
        "a token-like value is in an answer"
    )


@then('the connection test of the gmail account "{alias}" passes')
def step_test(context, alias):
    data = _ok(context.api.post(_url(context, f"accounts/{context.saved[f'{alias}_account_id']}/test/")))
    assert data["ok"] is True and "token" in data["checks"], data


@given('the gmail route "{key}" sends through the account "{alias}" with the DW mailbox "{dw}"')
def step_gmail_route(context, key, alias, dw):
    _remove_route(context, key)
    body = {
        "key": key,
        "name": "BDD",
        "from_email": context.saved[f"{alias}_email"],
        "cc_email": dw,
        "transport": "gmail_api",
        "mail_account_id": context.saved[f"{alias}_account_id"],
    }
    route = _ok(context.api.post(_url(context, "routes/"), json=body), 201)
    assert route["mail_account_state"] == "connected", route
    context.add_cleanup(_remove_route, context, key)


@given('a plain route "{key}" exists')
def step_plain_route(context, key):
    _remove_route(context, key)
    body = {"key": key, "name": "BDD", "from_email": f"bdd-{time.time_ns()}@ecom.example.test"}
    _ok(context.api.post(_url(context, "routes/"), json=body), 201)
    context.add_cleanup(_remove_route, context, key)


@when('I queue an approved "{template_key}" message to "{address}" on the gmail route "{route}" as "{alias}"')
def step_queue(context, template_key, address, route, alias):
    body = {
        "template_key": template_key,
        "recipient": {"email": address, "first_name": "Jan", "language": "pl", "legal_footer": LEGAL_FOOTER},
        "context": {"company_name": "Example Shop 1", "body": "BDD wiadomość testowa."},
        "subject_ref": f"bdd:gmail:{time.time_ns()}",
        "requires_review": False,
        "sender_route": route,
    }
    data = _ok(context.api.post(_url(context, "test/communicate/"), json=body), 201)
    assert data["status"] == "approved", data
    context.saved[alias], context.saved[f"{alias}_thread"] = data["id"], data["thread"]["id"]


@then('the test double holds {count:d} message sent by the account "{alias}"')
@then('the test double holds {count:d} messages sent by the account "{alias}"')
def step_sent_count(context, count, alias):
    assert len(_sent_by(context, alias)) == count, f"{len(_sent_by(context, alias))} messages in the double"


@then(
    'that message is from the account "{alias}" with a one-click List-Unsubscribe header and the DW mailbox "{dw}" kept out of the sandbox'
)
def step_message(context, alias, dw):
    sent = _parse(_sent_by(context, alias)[0]["raw"])
    assert context.saved[f"{alias}_email"] in sent["From"], sent["From"]
    assert sent["List-Unsubscribe"].startswith("<http") and "/public/unsubscribe/" in sent["List-Unsubscribe"], sent[
        "List-Unsubscribe"
    ]
    assert sent["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert sent["Message-ID"].endswith("@ecom.example.test>"), sent["Message-ID"]
    # sandbox: the real recipient and the real DW mailbox are never addressed, only named in headers
    assert sent["Subject"].startswith("[SANDBOX]") and sent["Cc"] is None, (sent["Subject"], sent["Cc"])
    assert sent["X-Original-Cc"] == dw and sent["X-Original-To"].startswith("bdd-gm2-a@"), (
        sent["X-Original-Cc"],
        sent["X-Original-To"],
    )


@when('the user revokes the access of the account "{alias}" in Google')
def step_revoke(context, alias):
    _stub("POST", "/__stub/revoke", {"email": context.saved[f"{alias}_email"]})


@then('the gmail account "{alias}" shows the state "{state}" and the error "{error}"')
def step_state_error(context, alias, state, error):
    account = _account(context, alias)
    assert (account["state"], account["last_error"]) == (state, error), account


@when('the recipient replies to the mail sent through the account "{alias}"')
def step_reply(context, alias):
    original = _parse(_sent_by(context, alias)[0]["raw"])
    mid = original["Message-ID"]
    raw = (
        f"From: Jan <bdd-gm4-a@example-shop-1.test>\r\nTo: {context.saved[f'{alias}_email']}\r\nSubject: Re: {original['Subject']}\r\n"
        f"Message-ID: <bdd-reply-{time.time_ns()}@example-shop-1.test>\r\nIn-Reply-To: {mid}\r\nReferences: {mid}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n\r\nChetnie porozmawiam, zadzwoń jutro.\r\n"
    )
    _stub("POST", "/__stub/inject", {"email": context.saved[f"{alias}_email"], "raw": raw})


@then('the thread of "{alias}" has exactly {count:d} reply')
def step_reply_count(context, alias, count):
    replies = _ok(context.api.get(_url(context, f"replies/?thread={context.saved[f'{alias}_thread']}")))["results"]
    assert len(replies) == count, f"{len(replies)} replies"
