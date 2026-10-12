# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The catalog file: categories and products from JSON or CSV, validated."""

import csv
import itertools
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from entirius_tests.data_package.profile import SKU_PATTERN, Profile

IMAGE_SEPARATOR = "|"
REMOTE_PREFIXES = ("http://", "https://")
PRODUCT_KEYS = ("sku", "name", "slug", "price", "quantity", "brand", "description")
ROOT_CATEGORY = "root"
SLUG_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
PRICE_PATTERN = re.compile(r"\d+(\.\d+)?")


@dataclass(frozen=True)
class Category:
    slug: str
    name: str
    parent: str | None


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    slug: str
    price: str
    category: str
    description: str
    images: tuple[Path, ...]
    quantity: int
    brand: str


@dataclass(frozen=True)
class Catalog:
    categories: tuple[Category, ...]
    products: tuple[Product, ...]


def slugify(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def _text(item: dict, key: str, where: str) -> str:
    """An optional text value; numbers are taken as written, anything else is refused."""
    value = item.get(key, "")
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise ValueError(f"{where}: {key} must be text, not {value!r}")
    return str(value).strip()


def _slug(item: dict, name: str, where: str) -> str:
    slug = _text(item, "slug", where) or slugify(name)
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError(f"{where}: slug {slug!r} must be lower-case letters, digits and hyphens (give a slug)")
    return slug


def _flatten(nodes: object, parent: str | None = None) -> Iterator[Category]:
    where = f"categories under {parent or 'the top level'}"
    if not isinstance(nodes, list) or not all(isinstance(node, dict) for node in nodes):
        raise ValueError(f"{where}: must be a list of objects")
    for node in nodes:
        if not (name := _text(node, "name", where)):
            raise ValueError(f"{where}: missing name")
        slug = _slug(node, name, f"category {name!r}")
        yield Category(slug, name, parent)
        yield from _flatten(node.get("children", []), slug)


def _read_json(path: Path) -> tuple[list[Category], list[dict]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path}: cannot read the catalog ({exc})") from exc
    if not isinstance(data, dict) or not isinstance(data.get("products"), list):
        raise ValueError(f"{path}: the catalog needs a products list")
    return list(_flatten(data.get("categories", []))), data["products"]


def _csv_product(row: dict) -> dict:
    product = {key: row[key] for key in PRODUCT_KEYS if row.get(key)}
    product["category_slug"] = row.get("category") or ""
    product["images"] = [image for image in (row.get("images") or "").split(IMAGE_SEPARATOR) if image]
    return product


def _read_csv(path: Path) -> tuple[list[Category], list[dict]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path}: cannot read the catalog ({exc})") from exc
    categories: dict[str, Category] = {}
    for row in rows:
        if (slug := row.get("category") or "") and slug not in categories:
            name = row.get("category_name") or slug.replace("-", " ").capitalize()
            categories[slug] = Category(
                _slug({"slug": slug}, name, f"category {name!r}"), name, row.get("parent_category") or None
            )
    return list(categories.values()), [_csv_product(row) for row in rows]


def _price(item: dict, where: str) -> str:
    price = _text(item, "price", where)
    if not PRICE_PATTERN.fullmatch(price) or not float(price) > 0:
        raise ValueError(f"{where}: price {item.get('price')!r} must be a decimal above 0, like '7.90'")
    return price


def _quantity(item: dict, where: str) -> int:
    quantity = _text(item, "quantity", where)
    if not quantity.isdecimal():
        raise ValueError(f"{where}: quantity {item.get('quantity')!r} must be a whole number, 0 or more")
    return int(quantity)


def _images(item: dict, base: Path, where: str) -> tuple[Path, ...]:
    values = item.get("images", [])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError(f"{where}: images must be a list of file paths")
    for value in values:
        if value.startswith(REMOTE_PREFIXES):
            raise ValueError(f"{where}: images are local files, not {value!r}")
        if not (base / value).is_file():
            raise ValueError(f"{where}: image file {base / value} does not exist")
    return tuple(base / value for value in values)


def _product(item: dict, row: int, base: Path) -> Product:
    where = f"product {row}"
    texts = {key: _text(item, key, where) for key in ("sku", "name", "category_slug", "description", "brand")}
    if missing := [key for key in ("name", "price", "category_slug") if not _text(item, key, where)]:
        raise ValueError(f"{where}: missing {missing[0]}")
    if not SKU_PATTERN.fullmatch(texts["sku"]):
        raise ValueError(f"{where}: sku {texts['sku']!r} must be letters, digits, dots, hyphens and underscores")
    if texts["brand"] and not slugify(texts["brand"]):
        raise ValueError(f"{where}: brand {texts['brand']!r} needs at least one letter or digit")
    return Product(
        sku=texts["sku"],
        name=texts["name"],
        slug=_slug(item, texts["name"], where),
        price=_price(item, where),
        category=texts["category_slug"],
        description=texts["description"],
        images=_images(item, base, where),
        quantity=_quantity(item, where),
        brand=texts["brand"],
    )


def _products(raw: list, base: Path, profile: Profile) -> tuple[Product, ...]:
    if not raw or not all(isinstance(item, dict) for item in raw):
        raise ValueError("catalog: products must be a list of at least one object")
    generated = (f"{profile.sku_prefix}-P{number:03d}" for number in itertools.count(1))
    defaults = {"quantity": profile.default_quantity}
    filled = [defaults | item | {"sku": item.get("sku") or next(generated)} for item in raw]
    return tuple(_product(item, row, base) for row, item in enumerate(filled, 1))


def _duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def _cycles(categories: tuple[Category, ...]) -> list[str]:
    """Categories whose chain of parents never reaches the top level."""
    parents = {category.slug: category.parent for category in categories}
    looping = []
    for slug in parents:
        seen, current = set(), slug
        while current is not None and current not in seen:
            seen.add(current)
            current = parents.get(current)
        looping += [slug] * (current is not None)
    return sorted(looping)


def _check(catalog: Catalog) -> None:
    slugs = [category.slug for category in catalog.categories]
    checks = {
        "reserved category slug": sorted({ROOT_CATEGORY} & set(slugs)),
        "duplicate category slug": _duplicates(slugs),
        "unknown parent category": sorted({c.parent for c in catalog.categories if c.parent} - set(slugs)),
        "category is its own ancestor": _cycles(catalog.categories),
        "duplicate sku": _duplicates([product.sku for product in catalog.products]),
        "duplicate product slug": _duplicates([product.slug for product in catalog.products]),
        "unknown category_slug": sorted({product.category for product in catalog.products} - set(slugs)),
    }
    for problem, values in checks.items():
        if values:
            raise ValueError(f"catalog: {problem}: {', '.join(values)}")


def load_catalog(path: str | Path, profile: Profile) -> Catalog:
    """The validated catalog of a .json or .csv file; ValueError names the product row or the value."""
    path = Path(path)
    readers = {".json": _read_json, ".csv": _read_csv}
    if (suffix := path.suffix.lower()) not in readers:
        raise ValueError(f"{path}: the catalog is a .json or a .csv file")
    categories, raw_products = readers[suffix](path)
    catalog = Catalog(tuple(categories), _products(raw_products, path.parent, profile))
    _check(catalog)
    return catalog
