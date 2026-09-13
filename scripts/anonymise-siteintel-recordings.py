# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Anonymise a private siteintel export into committable recordings.

    uv run python scripts/anonymise-siteintel-recordings.py --src <private export> --dst fixtures/siteintel

The export mirrors the recording layout: `psi/<domain>.{mobile,desktop}.json` and
`urlscan/<domain>.{submit,result}.json`. Every real domain becomes `example-shop-N.test` (first-seen order,
files sorted), every IPv4 `192.0.2.N`, every email `contact@example-shop-N.test`; base64 screenshots and
thumbnails are dropped. The domain mapping goes to stdout only — never into a file, never into a commit.
Exits 1 when `.pl` hosts outside the mapping remain in the output: review them before committing.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
from pathlib import Path

SUFFIXES = (".mobile.json", ".desktop.json", ".submit.json", ".result.json")
SCREENSHOT_KEY = re.compile(r"screenshot|thumbnail", re.IGNORECASE)
# not after `<letter>/`: `HeadlessChrome/131.0.0.0` is a version, `http://203.0.113.9` is an address
IPV4 = re.compile(r"(?<![\w.])(?<![A-Za-z]/)(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
IPV6 = re.compile(r"(?<![\w:])[0-9a-f]{0,4}(?::[0-9a-f]{0,4}){2,7}(?![\w:])", re.IGNORECASE)
# one pass for both families — a second pass would re-map the 192.0.2.N the first one wrote
IP = re.compile(f"{IPV4.pattern}|{IPV6.pattern}", re.IGNORECASE)
MAX_IPS = 254
# `%40` is a URL-encoded `@` — analytics query strings in urlscan request logs carry those
EMAIL = re.compile(r"[\w.+-]+(?:@|%40)([\w-]+\.)+[a-z]{2,}", re.IGNORECASE)
# a URL-encoded `/`, `:` or `@` right before a host must not shield it from replacement
DOMAIN_PREFIX = r"(?:(?<=%2F)|(?<=%3A)|(?<=%40)|(?<![\w.%-]))"
HOST = re.compile(r"(?<![\w.-])(?:[\w-]+\.)+[a-z]{2,}(?![\w-])", re.IGNORECASE)
REVIEW_TLD = re.compile(r"\.pl$", re.IGNORECASE)


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
        self.domain_re = re.compile(rf"{DOMAIN_PREFIX}(?:[\w-]+\.)*({pattern})(?![\w-])", re.IGNORECASE)

    def text(self, raw: str, own_domain: str) -> str:
        raw = EMAIL.sub(f"contact@{own_domain}", raw)
        raw = self.domain_re.sub(lambda m: self.domains[m.group(1).lower()], raw)
        return IP.sub(self._ip, raw)

    def _ip(self, match: re.Match) -> str:
        """Every valid IPv4/IPv6 address becomes one `192.0.2.N` (TEST-NET-1); anything else stays."""
        try:
            address = str(ipaddress.ip_address(match.group(0)))
        except ValueError:
            return match.group(0)
        if address not in self.ips and len(self.ips) >= MAX_IPS:
            raise SystemExit(f"more than {MAX_IPS} distinct IPs — TEST-NET-1 is exhausted")
        return self.ips.setdefault(address, f"192.0.2.{len(self.ips) + 1}")


def hosts_to_review(dst: Path) -> set[str]:
    """Hosts left in the output under the review TLD — client side domains the mapping did not know."""
    found = (HOST.findall(path.read_text(encoding="utf-8")) for path in dst.glob("*/*.json"))
    return {host.lower() for hosts in found for host in hosts if REVIEW_TLD.search(host)}


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
    if leftovers := hosts_to_review(args.dst):
        raise SystemExit(f"review before committing — unmapped hosts remain: {sorted(leftovers)}")


if __name__ == "__main__":
    main()
