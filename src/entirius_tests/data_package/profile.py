# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The profile file: one channel with its currency, languages, country and tax rate."""

import functools
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

REGIONAL_FILE = Path(__file__).parent / "data" / "regional-defaults.yaml"
CHANNEL_KEYS = ("idx", "name", "currency", "default_language", "languages", "default_country", "tax_rate")
IDX_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
SKU_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
TAX_RATE_PATTERN = re.compile(r"0(\.\d+)?")
DEFAULT_SKU_PREFIX = "SKU"


@dataclass(frozen=True)
class Profile:
    idx: str
    name: str
    currency: str
    default_language: str
    languages: tuple[str, ...]
    default_country: str
    tax_rate: str
    sku_prefix: str
    default_quantity: int


@functools.cache
def regional_rows(model: str) -> dict[str, dict]:
    """The fixture rows of one django_regional model, keyed by code (iso3 for a currency, iso2 otherwise)."""
    key = "iso3" if model == "currency" else "iso2"
    rows = yaml.safe_load(REGIONAL_FILE.read_text(encoding="utf-8"))
    return {row["fields"][key]: row for row in rows if row["model"] == f"django_regional.{model}"}


def regional_pk(model: str, code: str) -> int:
    return regional_rows(model)[code]["pk"]


def _check_code(model: str, key: str, code: str) -> None:
    if code not in (known := regional_rows(model)):
        raise ValueError(f"profile: {key} {code!r} is not a known {model} (known: {', '.join(sorted(known))})")


def _check(profile: Profile) -> None:
    if not IDX_PATTERN.fullmatch(profile.idx):
        raise ValueError(f"profile: channel.idx {profile.idx!r} must be lower-case letters, digits and hyphens")
    _check_code("currency", "channel.currency", profile.currency)
    _check_code("country", "channel.default_country", profile.default_country)
    for language in profile.languages:
        _check_code("language", "channel.languages", language)
    if profile.default_language not in profile.languages:
        raise ValueError(f"profile: channel.default_language {profile.default_language!r} is not in channel.languages")
    if len(set(profile.languages)) != len(profile.languages):
        raise ValueError("profile: channel.languages lists a language twice")
    if not SKU_PATTERN.fullmatch(profile.sku_prefix):
        raise ValueError(
            f"profile: sku_prefix {profile.sku_prefix!r} must be letters, digits, dots, hyphens, underscores"
        )


def _tax_rate(value: object) -> str:
    if not TAX_RATE_PATTERN.fullmatch(str(value)):
        raise ValueError(f"profile: channel.tax_rate {value!r} must be a decimal string from 0 up to 1, like '0.19'")
    return str(value)


def _quantity(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"profile: default_quantity {value!r} must be a whole number, 0 or more")
    return value


def _read(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"{path}: cannot read the profile ({exc})") from exc
    if not isinstance(data, dict) or not isinstance(data.get("channel"), dict):
        raise ValueError(f"{path}: the profile needs a channel mapping")
    return data


def load_profile(path: str | Path) -> Profile:
    """The validated profile; ValueError names the key that is missing or wrong."""
    data = _read(Path(path))
    channel = data["channel"]
    if missing := [key for key in CHANNEL_KEYS if channel.get(key) in (None, "", [])]:
        raise ValueError(f"{path}: missing channel.{', channel.'.join(missing)}")
    if not isinstance(channel["languages"], list) or not isinstance(channel["name"], str):
        raise ValueError(f"{path}: channel.languages must be a list and channel.name a text")
    profile = Profile(
        **{key: str(channel[key]) for key in ("idx", "name", "currency", "default_language", "default_country")},
        languages=tuple(str(language) for language in channel["languages"]),
        tax_rate=_tax_rate(channel["tax_rate"]),
        sku_prefix=str(data.get("sku_prefix", DEFAULT_SKU_PREFIX)),
        default_quantity=_quantity(data.get("default_quantity", 0)),
    )
    _check(profile)
    return profile
