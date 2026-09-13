# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Anonymise a private siteintel export into committable recordings.

    uv run python scripts/anonymise-siteintel-recordings.py --src <private export> --dst fixtures/siteintel
    uv run python scripts/anonymise-siteintel-recordings.py --verify fixtures/siteintel

The export mirrors the recording layout: `psi/<domain>.{mobile,desktop}.json` and
`urlscan/<domain>.{submit,result}.json`. The first seven domains (first-seen order, files sorted) become
`example-shop-N.test`, their label in free text `Example Shop N` (`example-shop-N` inside URLs), every other host
off the allowlist `third-party-N.test`, every IP `192.0.2.N` / `2001:db8::N`, every email
`contact@example-shop-N.test`; base64 screenshots, thumbnails and cookie headers are dropped. The domain mapping
goes to stdout only — never into a file, never into a commit.

The leak gate then scans every text file under the output (and `--verify` under an existing directory, which must
hold `psi/*.desktop.json` and `urlscan/*.{submit,result}.json`): any forbidden word of the repo's `.gitleaks.toml`
(rules `forbidden-names`, `entirius-parent-brand`) as a plain substring, any host off the allowlist whatever its TLD,
any other email, any IP outside the documentation/loopback ranges → redacted report on stderr, exit 1, output removed.
Forbidden words are never printed.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

SUFFIXES = (".mobile.json", ".desktop.json", ".submit.json", ".result.json")
RECORDING_DIRS = ("psi", "urlscan")
DOMAIN_COUNT = 7
GITLEAKS = Path(__file__).resolve().parent.parent / ".gitleaks.toml"
REVIEW_RULES = ("forbidden-names", "entirius-parent-brand")
# base64 images, plus the scanner's session cookies (a shop's CSRF `form_key` reads as a secret to gitleaks)
# and per-request random tokens (CDN request ids, NEL signatures) that can spell a forbidden word by chance
DROPPED_KEY = re.compile(r"screenshot|thumbnail|^(?:set-)?cookie$|^x-amz-cf-id$|^report-to$", re.IGNORECASE)
# wherever it sits (`host/203.0.113.9`, `ip=…`): a version string (`Chrome/119.0.0.0`) is replaced too
IPV4 = re.compile(r"(?<!\d)(?<!\d\.)(?:\d{1,3}\.){3}\d{1,3}(?!\.?\d)")
# at least one hex digit: a bare `::` (`::-webkit-scrollbar`) is CSS, not an address
IPV6 = re.compile(r"(?<![0-9a-f:])(?=[:0-9a-f]*[0-9a-f])[0-9a-f]{0,4}(?::[0-9a-f]{0,4}){2,7}(?![\w:])", re.IGNORECASE)
# one pass for both families; replacement and the leak gate share it, so they cannot drift
IP = re.compile(f"{IPV4.pattern}|{IPV6.pattern}", re.IGNORECASE)
ALLOWED_NETWORKS = tuple(
    ipaddress.ip_network(n) for n in ("192.0.2.0/24", "127.0.0.0/8", "0.0.0.0/32", "::1/128", "2001:db8::/32")
)
MAX_IPS = 254
# `%40` is a URL-encoded `@` — analytics query strings in urlscan request logs carry those
EMAIL = re.compile(r"[\w.+-]+(?:@|%40)((?:[\w-]+\.)+[a-z]{2,})", re.IGNORECASE)
# a URL-encoded character (`%2F`, `%20`, `%40`) right before a host must not shield it from replacement
# neither may a wildcard or cookie-domain dot (`*.shop.pl`, `".shop.pl"`)
DOMAIN_PREFIX = r"(?:(?<=%[0-9A-Fa-f]{2})|(?<![\w.%-])|(?<=[^\w.%-]\.))"
URL_ENCODED_OR_NOT_LETTER = r"(?:(?<=%[0-9A-Fa-f]{2})|(?<![a-z]))"
# a label this short is likely a common word (`unit` in `United`) — replaced as a word only
SHORT_LABEL = 4
# a host by structure, any TLD: `label(.label)+`, last label alphabetic 2–24 chars
HOST = re.compile(rf"{DOMAIN_PREFIX}(?:[a-z0-9-]+\.)+[a-z]{{2,24}}(?![\w-])", re.IGNORECASE)
# `main.js`, `logo.png` are files — none of these is a TLD
FILE_EXTENSIONS = set(
    "js mjs cjs ts vue css scss less jpg jpeg png gif webp avif svg ico html htm json xml php pdf ttf woff otf eot txt".split()
)
# `window.config`, `Array.prototype.map`, `div.item` are code — unless right after `//`
CODE_OBJECTS = set(
    "window document array object string promise reflect math json jquery lodash navigator location parent require"
    " domwindow xmlhttprequest gtm div span img ul li a p header footer strong section nav".split()
)
ALLOWED_HOSTS = (
    "localhost",
    "googleapis.com",  # Google APIs, fonts
    "urlscan.io",  # urlscan.io scanner
    "w3.org",  # W3C namespaces
    "schema.org",  # Schema.org vocabulary
    "gstatic.com",  # Google static CDN
    "google.com",  # Google
    "goo.gl",  # Google URL shortener
    "mail.ru",  # Mail.ru ad network
    "yandex.ru",  # Yandex ads and analytics
    "rambler.ru",  # Rambler SSP
    "teads.tv",  # Teads video ads
    "microad.jp",  # MicroAd ad network
)
SHOP_HOST = re.compile(r"(?:[\w-]+\.)*example-shop-\d+\.test|(?:[\w-]+\.)*third-party-\d+\.test", re.IGNORECASE)
SHOP_EMAIL = re.compile(r"contact(?:@|%40)example-shop-\d+\.test", re.IGNORECASE)
SECOND_LEVEL = {"com", "net", "org", "co", "waw"}
BASE64_STRING = re.compile(r'(?<=")[A-Za-z0-9+/=]{201,}(?=")')
REQUIRED_GLOBS = ("psi/*.desktop.json", "urlscan/*.submit.json", "urlscan/*.result.json")


def domain_of(path: Path) -> str:
    return next(path.name[: -len(suffix)] for suffix in SUFFIXES if path.name.endswith(suffix))


def recordings(src: Path) -> list[Path]:
    return sorted(p for p in src.glob("*/*.json") if p.parent.name in RECORDING_DIRS and p.name.endswith(SUFFIXES))


def map_domains(files: list[Path]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in files:
        mapping.setdefault(domain_of(path).lower(), f"example-shop-{len(mapping) + 1}.test")
    return mapping


def label_of(domain: str) -> str:
    """The registrable label: `sklep.shop.pl` → `shop`, `shop.waw.pl` → `shop`."""
    parts = domain.split(".")
    return parts[-3] if len(parts) >= 3 and parts[-2] in SECOND_LEVEL else parts[-2]


def strip_screenshots(node: object) -> object:
    """Drop screenshot/thumbnail/cookie keys and any base64 image payload, recursively."""
    if isinstance(node, dict):
        return {k: strip_screenshots(v) for k, v in node.items() if not DROPPED_KEY.search(k) and not is_image(v)}
    if isinstance(node, list):
        return [strip_screenshots(item) for item in node if not is_image(item)]
    return node


def is_image(value: object) -> bool:
    return isinstance(value, str) and value.startswith("data:image/")


def is_host(text: str, match: re.Match) -> bool:
    """A HOST match that is not a file name, a query-string key (`sst.adr=`) or a code expression."""
    labels = match.group(0).lower().split(".")
    if labels[-1] in FILE_EXTENSIONS or text.startswith("=", match.end()):
        return False
    return labels[0] not in CODE_OBJECTS or text[match.start() - 2 : match.start()] == "//"


def foreign_ip(literal: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """The parsed address unless it is not one or sits in a documentation/loopback range."""
    try:
        address = ipaddress.ip_address(literal)
    except ValueError:
        return None
    return None if any(address in network for network in ALLOWED_NETWORKS) else address


def is_allowed_host(host: str) -> bool:
    host = host.lower().rstrip(".")
    return bool(SHOP_HOST.fullmatch(host)) or any(host == a or host.endswith("." + a) for a in ALLOWED_HOSTS)


class Anonymiser:
    """Text-level replacement shared across files, so one IP or host keeps one alias everywhere."""

    def __init__(self, domains: dict[str, str]) -> None:
        self.domains = domains
        self.ips: dict[str, str] = {}
        self.ips6: dict[str, str] = {}
        self.hosts: dict[str, str] = {}
        # any subdomain (www., cdn., m.) collapses onto the alias — network logs are full of them
        pattern = "|".join(re.escape(d) for d in sorted(domains, key=len, reverse=True))
        self.domain_re = re.compile(rf"{DOMAIN_PREFIX}(?:[\w-]+\.)*({pattern})(?![\w-])", re.IGNORECASE)

    def text(self, raw: str, own_domain: str) -> str:
        fake = self.domains[own_domain]
        raw = EMAIL.sub(f"contact@{fake}", raw)
        raw = self.domain_re.sub(lambda m: self.domains[m.group(1).lower()], raw)
        raw = IP.sub(self._ip, raw)
        raw = HOST.sub(lambda m: self._host(raw, m), raw)
        return replace_label(raw, own_domain, fake)

    def _ip(self, match: re.Match) -> str:
        """IPv4 → `192.0.2.N` (TEST-NET-1), IPv6 → `2001:db8::N` (documentation prefix); anything else stays."""
        address = foreign_ip(match.group(0))
        if address is None:
            return match.group(0)
        aliases = self.ips if address.version == 4 else self.ips6
        if str(address) not in aliases and len(aliases) >= MAX_IPS:
            raise SystemExit(f"more than {MAX_IPS} distinct IPv{address.version} addresses — aliases exhausted")
        alias = f"192.0.2.{len(aliases) + 1}" if address.version == 4 else f"2001:db8::{len(aliases) + 1:x}"
        return aliases.setdefault(str(address), alias)

    def _host(self, raw: str, match: re.Match) -> str:
        host = match.group(0)
        if not is_host(raw, match) or is_allowed_host(host):
            return host
        return self.hosts.setdefault(host.lower(), f"third-party-{len(self.hosts) + 1}.test")


def replace_label(raw: str, domain: str, fake: str) -> str:
    """`Shop Lingerie` → `Example Shop N Lingerie`; `/video/shop_v9`, `/shoplingerie` → `/video/example-shop-N_v9`,
    `/example-shop-Nlingerie`."""
    slug = fake.removesuffix(".test")
    title = slug.replace("-", " ").title()

    def pick(match: re.Match) -> str:
        around = raw[match.start() - 1 : match.start()] + raw[match.end() : match.end() + 1]
        return slug if re.search(r"[\w/.%=&?-]", around) else title

    return re.sub(label_pattern(domain), pick, raw, flags=re.IGNORECASE)


def label_pattern(domain: str) -> str:
    """A long label is replaced wherever it appears (`/bizuteriashop`); a short one only as a word (`/shoppl`)."""
    label = label_of(domain)
    if len(label) > SHORT_LABEL:
        return re.escape(label)
    tld = re.escape(domain.rsplit(".", 1)[1])
    return rf"{URL_ENCODED_OR_NOT_LETTER}{re.escape(label)}(?=(?:{tld})?(?![a-z]))"


def convert(path: Path, src: Path, dst: Path, anonymiser: Anonymiser) -> None:
    real = domain_of(path)
    data = strip_screenshots(json.loads(path.read_text(encoding="utf-8")))
    body = anonymiser.text(json.dumps(data, ensure_ascii=False, indent=2), real.lower())
    fake = anonymiser.domains[real.lower()]
    target = dst / path.parent.relative_to(src) / (fake + path.name[len(real) :])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body + "\n", encoding="utf-8")


def load_review_words(words_file: Path | None) -> re.Pattern:
    """Forbidden words from the canonical blocklist, matched as plain substrings (a superset of the gitleaks rules,
    glued labels included); `--review-words-file` (one word per line) is the test hook."""
    if words_file:
        words = [w.strip() for w in words_file.read_text(encoding="utf-8").splitlines() if w.strip()]
        return re.compile("|".join(re.escape(w) for w in words), re.IGNORECASE)
    if not GITLEAKS.is_file():
        print("canonical .gitleaks.toml not found — run make check", file=sys.stderr)
        raise SystemExit(2)
    rules = tomllib.loads(GITLEAKS.read_text(encoding="utf-8"))["rules"]
    # the words are each rule's first capturing group; its boundary groups are dropped
    words = [re.search(r"\((?!\?)(.*?)\)", r["regex"]).group(1) for r in rules if r["id"] in REVIEW_RULES]
    return re.compile("|".join(f"(?:{group})" for group in words), re.IGNORECASE | re.VERBOSE)


def mask_base64(text: str) -> str:
    """Blank long pure-base64 JSON strings (same length, offsets kept) — random bytes spell words by chance."""
    return BASE64_STRING.sub(lambda m: " " * len(m.group(0)), text)


def leaks(text: str, forbidden: re.Pattern) -> list[re.Match]:
    """Every forbidden word, host off the allowlist, foreign email and foreign IP in one text."""
    text = mask_base64(text)
    found = list(forbidden.finditer(text))
    found += [m for m in HOST.finditer(text) if is_host(text, m) and not is_allowed_host(m.group(0))]
    found += [m for m in EMAIL.finditer(text) if not SHOP_EMAIL.fullmatch(m.group(0))]
    found += [m for m in IP.finditer(text) if foreign_ip(m.group(0))]
    return found


def excerpt(text: str, match: re.Match, forbidden: re.Pattern) -> str:
    """The hit as `***` with 30 characters around it; a forbidden word in the context is redacted too."""
    before = text[max(0, match.start() - 30) : match.start()]
    after = text[match.end() : match.end() + 30]
    return forbidden.sub("***", f"{before}***{after}").replace("\n", " ")


def text_files(root: Path) -> list[tuple[Path, str]]:
    """Every UTF-8 file under `root`, recursively; binaries are skipped."""
    found = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        try:
            found.append((path, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return found


def scan(root: Path, forbidden: re.Pattern) -> bool:
    """Report every leak in the text files under `root` to stderr (redacted); True when clean."""
    missing = [glob for glob in REQUIRED_GLOBS if not any(root.glob(glob))]
    if missing:
        print(f"not a recordings root: {root} lacks {', '.join(missing)}", file=sys.stderr)
        return False
    clean = True
    for path, text in text_files(root):
        for match in leaks(text, forbidden):
            line = text.count("\n", 0, match.start()) + 1
            print(f"LEAK {path}:{line}: {excerpt(text, match, forbidden)}", file=sys.stderr)
            clean = False
    return clean


def select_files(src: Path) -> list[Path]:
    files = recordings(src)
    domains = list(map_domains(files))
    if len(domains) < DOMAIN_COUNT:
        raise SystemExit(f"{len(domains)} domains under {src} — {DOMAIN_COUNT} needed, never fabricate recordings")
    keep = set(domains[:DOMAIN_COUNT])
    return [p for p in files if domain_of(p).lower() in keep]


def anonymise(src: Path, dst: Path) -> None:
    files = select_files(src)
    anonymiser = Anonymiser(map_domains(files))
    for path in files:
        convert(path, src, dst, anonymiser)
    for real, fake in anonymiser.domains.items():
        print(f"{fake} <- {real}")
    print(f"{len(files)} recordings written to {dst}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", type=Path, help="private export root (psi/, urlscan/)")
    parser.add_argument("--dst", type=Path, help="output root, e.g. fixtures/siteintel")
    parser.add_argument("--verify", type=Path, help="only run the leak gate on an existing output root")
    parser.add_argument("--review-words-file", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.verify and not (args.src and args.dst):
        parser.error("either --verify <dir> or both --src and --dst")
    return args


def main() -> None:
    args = parse_args()
    forbidden = load_review_words(args.review_words_file)
    if args.verify:
        raise SystemExit(0 if scan(args.verify, forbidden) else 1)
    anonymise(args.src, args.dst)
    if not scan(args.dst, forbidden):
        for name in RECORDING_DIRS:
            shutil.rmtree(args.dst / name, ignore_errors=True)
        raise SystemExit("leaks in the output — recordings removed, nothing to commit")


if __name__ == "__main__":
    main()
