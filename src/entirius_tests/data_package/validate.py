# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Read a built package back, without its inputs, and report what does not fit together."""

import csv
import json
from pathlib import Path

import yaml

from entirius_tests.data_package import csvs
from entirius_tests.data_package.fixtures import FIXTURES_DIR

MANIFEST = "manifest.json"
IMAGE_COLUMNS = ("img main", "images")


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _missing_files(root: Path, manifest: dict) -> list[str]:
    return [
        f"{name}: listed in {MANIFEST}, not in the package" for name in manifest["files"] if not (root / name).is_file()
    ]


def _channel_problems(root: Path, idx: str) -> list[str]:
    conf = (root / csvs.CHANNELS_CONF).read_text(encoding="utf-8").split()
    declared = {
        csvs.CHANNELS_CONF: [line.split(":")[0] for line in conf],
        csvs.PIM_CHANNELS: [row["idx"] for row in _rows(root / csvs.PIM_CHANNELS)],
    }
    return [f"{name}: channel {found} is not [{idx!r}]" for name, found in declared.items() if found != [idx]]


def _fixture_problems(root: Path, manifest: dict, idx: str) -> list[str]:
    problems = []
    for name in manifest["fixtures"]:
        try:
            records = yaml.safe_load((root / FIXTURES_DIR / name).read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            problems.append(f"{FIXTURES_DIR}/{name}: does not parse ({exc})")
            continue
        channels = [record["fields"]["idx"] for record in records if record["model"].endswith(".channel")]
        problems += [f"{FIXTURES_DIR}/{name}: channel {found!r} is not {idx!r}" for found in channels if found != idx]
    return problems


def _image_paths(row: dict) -> list[str]:
    return [path for column in IMAGE_COLUMNS for path in (row.get(column) or "").split(",") if path]


def _product_problems(root: Path, idx: str) -> list[str]:
    categories = {row["idx"] for row in _rows(root / csvs.categories_file(idx))}
    known = {
        "pricelist row": {row["sku"] for row in _rows(root / csvs.pricelist_file(idx))},
        "qty row": {row["sku"] for row in _rows(root / csvs.QTY_FILE)},
    }
    problems = []
    for row in _rows(root / csvs.products_file(idx)):
        sku = row["sku"]
        problems += [f"product {sku}: no {what}" for what, skus in known.items() if sku not in skus]
        problems += [f"product {sku}: unknown category {row['category']}"] * (row["category"] not in categories)
        images = [path for path in _image_paths(row) if not (root / csvs.PACKAGE_DIR / path).is_file()]
        problems += [f"product {sku}: image {path} is not in the package" for path in images]
    return problems


def _counts(root: Path, idx: str) -> dict[str, int]:
    return {
        "categories": len(_rows(root / csvs.categories_file(idx))),
        "products": len(_rows(root / csvs.products_file(idx))),
        "images": sum(1 for path in (root / csvs.IMAGES_DIR).rglob("*") if path.is_file()),
    }


def _content_problems(root: Path, manifest: dict) -> list[str]:
    idx = manifest["channel"]
    problems = [
        *_channel_problems(root, idx),
        *_fixture_problems(root, manifest, idx),
        *_product_problems(root, idx),
    ]
    if (counts := _counts(root, idx)) != manifest["counts"]:
        problems.append(f"{MANIFEST}: counts {manifest['counts']} do not match the package {counts}")
    return problems


def validate(root: Path) -> tuple[str, list[str]]:
    """The summary line of a package and its problems (an empty list: the package is valid)."""
    try:
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
        problems = _missing_files(root, manifest) or _content_problems(root, manifest)
        counts = manifest["counts"]
        summary = f"{manifest['channel']} ({counts['categories']} categories, {counts['products']} products"
    except (OSError, ValueError, LookupError, TypeError, AttributeError) as exc:
        return "", [f"{root}: damaged package, cannot be read ({type(exc).__name__}: {exc})"]
    return f"{summary}, {counts['images']} images)", problems
