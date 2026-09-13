# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Anonymise a private siteintel export into committable recordings.

    uv run python scripts/anonymise-siteintel-recordings.py --src <private export> --dst fixtures/siteintel

The export mirrors the recording layout: `psi/<domain>.{mobile,desktop}.json` and
`urlscan/<domain>.{submit,result}.json`. Every real domain becomes `example-shop-N.test` (first-seen order,
files sorted), every IPv4 `192.0.2.N`, every email `contact@example-shop-N.test`; base64 screenshots and
thumbnails are dropped. The domain mapping goes to stdout only — never into a file, never into a commit.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SUFFIXES = (".mobile.json", ".desktop.json", ".submit.json", ".result.json")
SCREENSHOT_KEY = re.compile(r"screenshot|thumbnail", re.IGNORECASE)
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EMAIL = re.compile(r"[\w.+-]+@([\w-]+\.)+[a-z]{2,}", re.IGNORECASE)


def domain_of(path: Path) -> str:
    return next(path.name[: -len(suffix)] for suffix in SUFFIXES if path.name.endswith(suffix))


def recordings(src: Path) -> list[Path]:
    return sorted(p for p in src.glob("*/*.json") if p.parent.name in ("psi", "urlscan") and p.name.endswith(SUFFIXES))


def map_domains(files: list[Path]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in files:
        mapping.setdefault(domain_of(path), f"example-shop-{len(mapping) + 1}.test")
    return mapping


def strip_screenshots(node: object) -> object:
    """Drop screenshot/thumbnail keys and any base64 image payload, recursively."""
    if isinstance(node, dict):
        return {k: strip_screenshots(v) for k, v in node.items() if not SCREENSHOT_KEY.search(k) and not is_image(v)}
    if isinstance(node, list):
        return [strip_screenshots(item) for item in node if not is_image(item)]
    return node


def is_image(value: object) -> bool:
    return isinstance(value, str) and value.startswith("data:image/")


class Anonymiser:
    """Text-level replacement shared across files, so one IP or domain keeps one alias everywhere."""

    def __init__(self, domains: dict[str, str]) -> None:
        self.domains = domains
        self.ips: dict[str, str] = {}
        # any subdomain (www., cdn., m.) collapses onto the alias — network logs are full of them
        pattern = "|".join(re.escape(d) for d in sorted(domains, key=len, reverse=True))
        self.domain_re = re.compile(rf"(?<![\w.-])(?:[\w-]+\.)*({pattern})(?![\w-])", re.IGNORECASE)

    def text(self, raw: str, own_domain: str) -> str:
        raw = EMAIL.sub(f"contact@{own_domain}", raw)
        raw = self.domain_re.sub(lambda m: self.domains[m.group(1).lower()], raw)
        return IPV4.sub(self._ip, raw)

    def _ip(self, match: re.Match) -> str:
        return self.ips.setdefault(match.group(0), f"192.0.2.{len(self.ips) + 1}")


def convert(path: Path, src: Path, dst: Path, anonymiser: Anonymiser) -> None:
    real = domain_of(path)
    fake = anonymiser.domains[real.lower()]
    data = strip_screenshots(json.loads(path.read_text(encoding="utf-8")))
    body = anonymiser.text(json.dumps(data, ensure_ascii=False, indent=2), fake)
    target = dst / path.parent.relative_to(src) / (fake + path.name[len(real) :])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", type=Path, required=True, help="private export root (psi/, urlscan/)")
    parser.add_argument("--dst", type=Path, required=True, help="output root, e.g. fixtures/siteintel")
    args = parser.parse_args()
    files = recordings(args.src)
    if not files:
        raise SystemExit(f"no recordings under {args.src}/psi or {args.src}/urlscan")
    domains = {d.lower(): fake for d, fake in map_domains(files).items()}
    anonymiser = Anonymiser(domains)
    for path in files:
        convert(path, args.src, args.dst, anonymiser)
    for real, fake in domains.items():
        print(f"{fake} <- {real}")
    print(f"{len(files)} recordings written to {args.dst}")


if __name__ == "__main__":
    main()
