# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def _load_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_products(package_path: str, channel: str) -> list[dict[str, str]]:
    return _load_csv(Path(package_path) / f"products--{channel}.csv")


def load_categories(package_path: str, channel: str) -> list[dict[str, str]]:
    return _load_csv(Path(package_path) / f"categories--{channel}.csv")


def load_pricelist(package_path: str, channel: str) -> list[dict[str, str]]:
    return _load_csv(Path(package_path) / f"pricelist--{channel}.csv")


def load_quantities(package_path: str) -> list[dict[str, str]]:
    return _load_csv(Path(package_path) / "qty.csv")


def load_attributes(package_path: str, attr_type: str) -> list[dict[str, str]]:
    return _load_csv(Path(package_path) / f"attributes--{attr_type}.csv")


def load_feature_sets(package_path: str) -> list[dict[str, str]]:
    return _load_csv(Path(package_path) / "volkanos-config" / "pim-features-sets.csv")


def load_product_positions(package_path: str, channel: str) -> list[dict[str, str]]:
    return _load_csv(Path(package_path) / f"products-position--{channel}.csv")


def get_category_url_key_map(package_path: str, channel: str) -> dict[str, str]:
    """Map category idx -> url_key en from categories CSV."""
    categories = load_categories(package_path, channel)
    return {row["idx"]: row.get("url key en", row["idx"]) for row in categories if row.get("idx")}


def expected_sku_order_for_category(package_path: str, channel: str, category_url_key: str) -> list[str]:
    """Return expected SKU order for a category_url_key based on positions CSV.

    Maps category url_key back to idx via categories CSV, then sorts
    positions CSV entries for that category by position.
    """
    url_key_map = get_category_url_key_map(package_path, channel)
    # Reverse: url_key -> idx
    idx_by_url_key = {v: k for k, v in url_key_map.items()}
    category_idx = idx_by_url_key.get(category_url_key, category_url_key)

    positions = load_product_positions(package_path, channel)
    category_rows = [row for row in positions if row.get("category_idx") == category_idx]
    category_rows.sort(key=lambda r: int(r.get("position", 0)))
    return [row["sku"] for row in category_rows]


def load_products_by_type(package_path: str, channel: str, product_type: str) -> list[dict[str, str]]:
    """Filter products CSV by product type column."""
    products = load_products(package_path, channel)
    if product_type == "simple":
        return [p for p in products if not p.get("product type", "").strip()]
    return [p for p in products if p.get("product type", "").strip().lower() == product_type.lower()]


def count_products_by_type(package_path: str, channel: str) -> dict[str, int]:
    """Count products per type: {simple: N, config: N, bundle: N, custom: N}."""
    products = load_products(package_path, channel)
    counts: Counter[str] = Counter()
    for p in products:
        ptype = p.get("product type", "").strip().lower()
        if not ptype:
            ptype = "simple"
        counts[ptype] += 1
    return dict(counts)


def load_discount_rules(package_path: str) -> list[dict[str, str]]:
    """Load discount rules from discount-rules.csv."""
    return _load_csv(Path(package_path) / "discount-rules.csv")


def get_discount_rule_by_name(package_path: str, name: str) -> dict[str, str] | None:
    """Get a specific discount rule by name."""
    rules = load_discount_rules(package_path)
    for rule in rules:
        if rule.get("name") == name:
            return rule
    return None


def get_discount_rule_by_code(package_path: str, code: str) -> dict[str, str] | None:
    """Get a specific discount rule by code."""
    rules = load_discount_rules(package_path)
    for rule in rules:
        if rule.get("code") == code:
            return rule
    return None
