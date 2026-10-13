#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Fail when the text on stdin carries an access token or a legacy fixture key (stdlib only).

    docker compose … logs service worker | python3 scripts/secret_scan.py --fixtures fixtures
    redis-cli --scan | python3 scripts/secret_scan.py --fixtures fixtures
    python3 scripts/secret_scan.py --self-test

Prints one count per pattern — never a match — and exits 1 when any count is above zero. The legacy literals are
the `key:` values of the `django_*.apikey` entries of the fixture YAML files under `--fixtures`; none found = exit 2.
"""

from __future__ import annotations

import argparse
import re
import secrets
import sys
from pathlib import Path

TOKEN_LABEL = "ent_api_ token"  # noqa: S105 — a report label, not a secret
TOKEN_PATTERN = re.compile(r"ent_api_[A-Za-z0-9_-]{43}")
APIKEY_ENTRY = re.compile(r"^- model:\s*(django_\w+\.apikey)\s*$(.*?)(?=^- |\Z)", re.M | re.S | re.I)
PK_LINE = re.compile(r"^\s+pk:\s*(\S+)", re.M)
KEY_LINE = re.compile(r"^\s+key:\s*['\"]?([^'\"\s]+)", re.M)


def fixture_literals(directory: Path) -> dict[str, str]:
    """`<model>#<pk>` → the legacy key literal of every `django_*.apikey` fixture entry."""
    literals = {}
    for path in sorted(directory.glob("*.yaml")):
        for model, block in APIKEY_ENTRY.findall(path.read_text(encoding="utf-8")):
            pk, key = PK_LINE.search(block), KEY_LINE.search(block)
            if key:
                literals[f"{model.lower()}#{pk.group(1) if pk else '?'}"] = key.group(1)
    return literals


def scan(text: str, literals: dict[str, str]) -> dict[str, int]:
    """Occurrences per pattern label."""
    counts = {TOKEN_LABEL: len(TOKEN_PATTERN.findall(text))}
    counts.update({f"fixture key {label}": text.count(literal) for label, literal in literals.items()})
    return counts


def report(counts: dict[str, int]) -> list[str]:
    return [f"secret_scan: {label}: {count}" for label, count in counts.items()]


def self_test() -> bool:
    """A generated fake token and a generated fake literal planted in a log line must both be found."""
    token, literal = f"ent_api_{secrets.token_urlsafe(32)}", secrets.token_hex(16)
    literals = {"self-test#1": literal}
    planted = scan(f"GET /x HTTP/1.1 key={token} other={literal}\n", literals)
    clean = scan("GET /x HTTP/1.1 200\n", literals)
    lines = report(planted)
    found = planted == {TOKEN_LABEL: 1, "fixture key self-test#1": 1} and not any(clean.values())
    quiet = not any(token in line or literal in line for line in lines)
    return found and quiet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixtures", type=Path, help="directory of fixture YAML files with legacy keys")
    parser.add_argument("--self-test", action="store_true", help="plant generated fakes and require detection")
    args = parser.parse_args()
    if args.self_test:
        ok = self_test()
        print(f"secret_scan: self-test {'ok' if ok else 'FAILED'}")
        return 0 if ok else 1
    literals = fixture_literals(args.fixtures) if args.fixtures else {}
    if args.fixtures and not literals:  # a wrong path or a changed format must not pass as "clean"
        print(f"secret_scan: no legacy key literal found under {args.fixtures}")
        return 2
    counts = scan(sys.stdin.read(), literals)
    print("\n".join(report(counts)))
    return 1 if any(counts.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
