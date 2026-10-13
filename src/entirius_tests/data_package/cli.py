# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Command line: `build` a data package from a profile and a catalog file, `validate` a built one."""

import argparse
import json
from pathlib import Path

from entirius_tests.data_package.catalog import Catalog, load_catalog
from entirius_tests.data_package.csvs import write_csvs
from entirius_tests.data_package.fixtures import FIXTURES_DIR, write_fixtures
from entirius_tests.data_package.images import copy_images
from entirius_tests.data_package.profile import Profile, load_profile
from entirius_tests.data_package.validate import MANIFEST, validate

PROG = "data-package"
FIRST_CHANNEL = "first-channel.toml"


def _say(message: str) -> None:
    print(f"{PROG}: {message}", flush=True)


def _toml_list(values: tuple[str, ...]) -> str:
    return f"[{', '.join(json.dumps(value) for value in values)}]"


def _first_channel(profile: Profile) -> str:
    """The config the service's first-channel script reads: seven keys of one `[channel]` table."""
    values = {
        "idx": json.dumps(profile.idx),
        "name": json.dumps(profile.name),
        "default_language": json.dumps(profile.default_language),
        "languages": _toml_list(profile.languages),
        "default_currency": json.dumps(profile.currency),
        "currencies": _toml_list((profile.currency,)),
        "country": json.dumps(profile.default_country),
    }
    return "[channel]\n" + "".join(f"{key} = {value}\n" for key, value in values.items())


def _counts(catalog: Catalog) -> dict[str, int]:
    return {
        "categories": len(catalog.categories) + 1,  # the root row
        "products": len(catalog.products),
        "images": sum(len(product.images) for product in catalog.products),
    }


def _prepare(out: Path) -> None:
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError(f"{out}: the output directory exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)


def _write_manifest(out: Path, manifest: dict) -> None:
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    catalog = load_catalog(args.catalog, profile)
    out = Path(args.out).resolve()
    mount = (args.mount or str(out)).rstrip("/")
    _prepare(out)
    files = [*write_csvs(profile, catalog, out), *copy_images(catalog, out), FIRST_CHANNEL]
    fixtures = write_fixtures(profile, out, mount)
    (out / FIRST_CHANNEL).write_text(_first_channel(profile), encoding="utf-8")
    files = sorted([*files, *(f"{FIXTURES_DIR}/{name}" for name in fixtures)])
    counts = _counts(catalog)
    _write_manifest(
        out, {"channel": profile.idx, "mount": mount, "fixtures": fixtures, "counts": counts, "files": files}
    )
    for name in [*files, MANIFEST]:
        _say(f"wrote {name}")
    _say(f"done {profile.idx} -> {out}")
    return 0


def _validate(args: argparse.Namespace) -> int:
    summary, problems = validate(Path(args.package))
    for problem in problems:
        _say(f"invalid: {problem}")
    if not problems:
        _say(f"valid {summary}")
    return 1 if problems else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=f"python -m entirius_tests.{PROG.replace('-', '_')}", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="write a data package into an empty directory")
    build.add_argument("--profile", required=True, help="profile.yaml: channel, currency, languages, country, tax rate")
    build.add_argument("--catalog", required=True, help="catalog.json or catalog.csv: categories and products")
    build.add_argument("--out", required=True, help="output directory (new or empty)")
    build.add_argument("--mount", help="the path of the package where the service reads it (default: --out)")
    build.set_defaults(run=_build)
    check = commands.add_parser("validate", help="read a built package back and report what does not fit")
    check.add_argument("package", help="the directory a build wrote")
    check.set_defaults(run=_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.run(args)
    except (ValueError, OSError) as exc:
        _say(f"error: {exc}")
        return 1
