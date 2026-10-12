# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The `package/` directory: PIM configuration, attributes, categories, products, prices, quantities."""

import csv
from pathlib import Path

from entirius_tests.data_package.catalog import ROOT_CATEGORY, Catalog, Category, Product, slugify
from entirius_tests.data_package.profile import Profile

PACKAGE_DIR = "package"
CONFIG_DIR = f"{PACKAGE_DIR}/volkanos-config"
CHANNELS_CONF = f"{CONFIG_DIR}/channels.conf"
PIM_CHANNELS = f"{CONFIG_DIR}/pim-channels.csv"
QTY_FILE = f"{PACKAGE_DIR}/qty.csv"
IMAGES_DIR = "images"
FEATURE_SET = "default"
TAX_CLASS = "standard-rate"
Table = tuple[list[str], list[list[str]]]
FEATURE_SETS: Table = (["idx", "name", "desc", "is-default", "features"], [[FEATURE_SET, "Default", "", "TRUE", ""]])
FEATURE_POSITIONS: Table = (["feature-idx", "feature-set-idx", "position"], [])

# The system features of a PIM installation: idx, type, name, then visible, required, filterable, searchable.
SYSTEM_FEATURES = (
    ("name", "text t9n", "Name", "TRUE", "TRUE", "FALSE", "TRUE"),
    ("description", "text t9n", "Description", "TRUE", "FALSE", "FALSE", "TRUE"),
    ("short_description", "text t9n", "Description Short", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("url_key", "varchar 255 t9n", "Url key", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("badge", "multiselect", "Badge", "TRUE", "FALSE", "FALSE", "FALSE"),
    ("brand", "select", "Brand", "TRUE", "FALSE", "FALSE", "FALSE"),
    ("subname", "text t9n", "Subname 1", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("subname2", "text t9n", "Subname 2", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("size_table", "json", "Size Table", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("extension", "json", "Extension", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("meta_title", "text t9n", "Meta title", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("meta_description", "text t9n", "Meta description", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("rich_content", "json", "Rich Content", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("canonical_url", "varchar 255 t9n", "Canonical URL", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("og_image", "varchar 255 t9n", "OG Image", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("max_limit_bundle", "varchar 255 t9n", "Max Bundle Limit", "FALSE", "FALSE", "FALSE", "FALSE"),
    ("min_limit_bundle", "varchar 255 t9n", "Min Bundle Limit", "FALSE", "FALSE", "FALSE", "FALSE"),
)


def products_file(idx: str) -> str:
    return f"{PACKAGE_DIR}/products--{idx}.csv"


def categories_file(idx: str) -> str:
    return f"{PACKAGE_DIR}/categories--{idx}.csv"


def pricelist_file(idx: str) -> str:
    return f"{PACKAGE_DIR}/pricelist--{idx}.csv"


def image_path(sku: str, number: int, source: Path) -> str:
    """Where image `number` of a product lives, relative to the package root."""
    return f"{IMAGES_DIR}/{sku}/{number}{source.suffix.lower()}"


def _per_language(profile: Profile, field: str) -> list[str]:
    return [f"{field} {language}" for language in profile.languages]


def _channels(profile: Profile) -> Table:
    languages = ",".join(profile.languages)
    currency = profile.currency.lower()
    header = ["idx", "name", "default_language", "languages", "default_currency", "currencies"]
    return header, [[profile.idx, profile.name, profile.default_language, languages, currency, currency]]


def _features(profile: Profile) -> Table:
    header = ["idx", "scope", "type", *_per_language(profile, "name")]
    rows = [
        [idx, "system", kind, *[name] * len(profile.languages), *flags] for idx, kind, name, *flags in SYSTEM_FEATURES
    ]
    return [*header, "visible", "required", "filterable", "searchable"], rows


def _brands(profile: Profile, catalog: Catalog) -> Table:
    brands: dict[str, str] = {}
    for product in catalog.products:
        if product.brand:
            brands.setdefault(slugify(product.brand), product.brand)
    rows = [[idx, *[name] * len(profile.languages)] for idx, name in brands.items()]
    return ["idx", *_per_language(profile, "name")], rows


def _category_row(category: Category, order: int, languages: int) -> list[str]:
    """One category; the importer requires a description, so the name stands in for it."""
    parent = ROOT_CATEGORY if category.parent is None else category.parent
    texts = [*[category.name] * 2 * languages, *[category.slug] * languages]
    return [category.slug, parent, *texts, str(10 * order), "true", "true"]


def _categories(profile: Profile, catalog: Catalog) -> Table:
    fields = ("name", "description", "url key")
    header = ["idx", "parent", *[column for field in fields for column in _per_language(profile, field)]]
    tree = [Category(ROOT_CATEGORY, "Root", ""), *catalog.categories]
    rows = [_category_row(category, order, len(profile.languages)) for order, category in enumerate(tree)]
    return [*header, "position", "is in menu", "is active"], rows


def _product_row(product: Product, languages: int) -> list[str]:
    paths = [f"../{image_path(product.sku, n, image)}" for n, image in enumerate(product.images, 1)]
    texts = [*[product.name] * languages, *[product.slug] * languages, *[product.description] * languages]
    main, gallery = "".join(paths[:1]), ",".join(paths[1:])
    return [product.sku, FEATURE_SET, product.category, slugify(product.brand), *texts, main, gallery]


def _products(profile: Profile, catalog: Catalog) -> Table:
    fields = ("name", "url_key", "description")
    header = ["sku", "feature set", "category", "brand", *[c for f in fields for c in _per_language(profile, f)]]
    rows = [_product_row(product, len(profile.languages)) for product in catalog.products]
    return [*header, "img main", "images"], rows


def _pricelist(catalog: Catalog) -> Table:
    rows = [[product.sku, TAX_CLASS, product.price, ""] for product in catalog.products]
    return ["sku", "tax_class", "gross", "special_price_gross"], rows


def _quantities(catalog: Catalog) -> Table:
    return ["sku", "quantity"], [[product.sku, str(product.quantity)] for product in catalog.products]


def _tables(profile: Profile, catalog: Catalog) -> dict[str, Table]:
    return {
        PIM_CHANNELS: _channels(profile),
        f"{CONFIG_DIR}/pim-features.csv": _features(profile),
        f"{CONFIG_DIR}/pim-features-sets.csv": FEATURE_SETS,
        f"{CONFIG_DIR}/pim-feature-position-in-features-sets.csv": FEATURE_POSITIONS,
        f"{PACKAGE_DIR}/attributes--brand.csv": _brands(profile, catalog),
        categories_file(profile.idx): _categories(profile, catalog),
        products_file(profile.idx): _products(profile, catalog),
        pricelist_file(profile.idx): _pricelist(catalog),
        QTY_FILE: _quantities(catalog),
    }


def write_csvs(profile: Profile, catalog: Catalog, out: Path) -> list[str]:
    """Write the package files; returns their paths relative to `out`."""
    (out / CONFIG_DIR).mkdir(parents=True)
    (out / CHANNELS_CONF).write_text(f"{profile.idx}:{profile.currency}\n", encoding="utf-8")
    tables = _tables(profile, catalog)
    for name, (header, rows) in tables.items():
        with (out / name).open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle, lineterminator="\n").writerows([header, *rows])
    return [CHANNELS_CONF, *tables]
