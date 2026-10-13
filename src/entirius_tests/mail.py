# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""GreenMail mail sandbox helpers (zeno `make mail`): purge, count and read over REST, send over SMTP,
inject over IMAP. GreenMail has no inject endpoint — IMAP APPEND is the inject.

Host-side ports follow the zeno +100 convention; containers talk to `greenmail:3025/3143/8080` instead.
GreenMail runs with authentication disabled, so any login works; the sandbox user's password is its login.
"""

from __future__ import annotations

import email
import imaplib
import os
import smtplib
import time
from email.message import Message
from email.utils import make_msgid
from pathlib import Path

import requests

GREENMAIL_API_URL = os.environ.get("GREENMAIL_API_URL", "http://localhost:8380")
GREENMAIL_HOST = "localhost"
GREENMAIL_SMTP_PORT = int(os.environ.get("GREENMAIL_SMTP_PORT", "3125"))
GREENMAIL_IMAP_PORT = int(os.environ.get("GREENMAIL_IMAP_PORT", "3243"))
SANDBOX_USER = "sandbox"
SANDBOX_EMAIL = "sandbox@greenmail.test"
PURGE_PATH = "/api/mail/purge"
READINESS_PATH = "/api/service/readiness"
MESSAGE_ID_PLACEHOLDER = b"{message_id}"
TIMEOUT_S = 10


def ready() -> bool:
    """True when the GreenMail REST API answers its readiness probe."""
    try:
        return requests.get(f"{GREENMAIL_API_URL}{READINESS_PATH}", timeout=TIMEOUT_S).ok
    except requests.RequestException:
        return False


def purge() -> None:
    """Delete every message of every user."""
    requests.post(f"{GREENMAIL_API_URL}{PURGE_PATH}", timeout=TIMEOUT_S).raise_for_status()


def list_messages(user: str = SANDBOX_USER, folder: str = "INBOX") -> list[dict]:
    """Messages of a user's folder, oldest first (`uid`, `messageId`, `subject`, `mimeMessage`)."""
    resp = requests.get(f"{GREENMAIL_API_URL}/api/user/{user}/messages/{folder}", timeout=TIMEOUT_S)
    resp.raise_for_status()
    return sorted(resp.json(), key=lambda message: int(message["uid"]))


def count(user: str = SANDBOX_USER) -> int:
    return len(list_messages(user))


def get_message(uid: int | str, user: str = SANDBOX_USER) -> Message:
    """The parsed MIME message with the given IMAP uid."""
    for message in list_messages(user):
        if str(message["uid"]) == str(uid):
            return email.message_from_string(message["mimeMessage"])
    raise LookupError(f"no message uid={uid} for user {user!r}")


def wait_for_count(n: int, user: str = SANDBOX_USER, timeout: float = 20) -> int:
    """Poll until the mailbox holds at least `n` messages or `timeout` elapses; returns the last count."""
    deadline = time.monotonic() + timeout
    while (current := count(user)) < n and time.monotonic() < deadline:
        time.sleep(0.5)
    return current


def render_fixture(path: Path, message_id: str | None = None) -> bytes:
    """Fixture `.eml` bytes with `{message_id}` (In-Reply-To / References / Original-Message-ID) replaced.

    Without a `message_id` a fresh one is generated, so the headers stay RFC 5322-valid.
    """
    mid = (message_id or make_msgid(domain="greenmail.test")).strip("<>")
    return path.read_bytes().replace(MESSAGE_ID_PLACEHOLDER, f"<{mid}>".encode())


def send_raw(eml: bytes, sender: str, recipients: list[str]) -> None:
    """Deliver raw RFC 5322 bytes through the GreenMail SMTP port."""
    with smtplib.SMTP(GREENMAIL_HOST, GREENMAIL_SMTP_PORT, timeout=TIMEOUT_S) as smtp:
        smtp.sendmail(sender, recipients, eml)


def inject(path: Path, *, user: str = SANDBOX_USER, folder: str = "INBOX", message_id: str | None = None) -> None:
    """Place a fixture `.eml` straight into a folder (IMAP APPEND), as if it had been received."""
    append_raw(render_fixture(path, message_id), user=user, folder=folder)


def append_raw(eml: bytes, *, user: str = SANDBOX_USER, folder: str = "INBOX") -> None:
    """IMAP APPEND raw RFC 5322 bytes to a folder."""
    with imaplib.IMAP4(GREENMAIL_HOST, GREENMAIL_IMAP_PORT, timeout=TIMEOUT_S) as imap:
        imap.login(user, user)
        status, detail = imap.append(folder, None, None, eml)
        if status != "OK":
            raise RuntimeError(f"IMAP APPEND to {user}/{folder} failed: {detail}")
