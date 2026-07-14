# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Devtools Multiplier — Bulk data generation for stress testing.

Runs inside Docker container via: python manage.py shell < multiply.py
Configured by environment variables (see README.md).

Creates PIM-only data (no prices, quantities, or Matrix).
Run fill commands after multiplication for full API availability.
"""

from __future__ import annotations

import os
import struct
import sys
import time
import zlib

import django

django.setup()

from django.db import connection  # noqa: E402
from django_pim.models import (  # noqa: E402
    Attribute,
    Feature,
    FeatureInFeatureSet,
    FeatureSet,
    Picture,
    Product,
    ProductAttribute,
    ProductCategory,
    ProductInCategory,
    ProductLink,
    ProductLinkType,
    ProductPicture,
    ProductSimple,
    RealProduct,
)

ENTITY = os.environ.get("MULTIPLY_ENTITY", "products")
COUNT = int(os.environ.get("MULTIPLY_COUNT", "1000"))
CHANNEL = os.environ.get("MULTIPLY_CHANNEL", "")
BATCH_SIZE = int(os.environ.get("MULTIPLY_BATCH_SIZE", "500"))
SKU = os.environ.get("MULTIPLY_SKU", "")


def _timer(label: str):
    """Context manager that prints elapsed time."""

    class Timer:
        def __enter__(self):
            self.start = time.time()
            print(f"  [{label}] starting...")
            return self

        def __exit__(self, *_):
            elapsed = time.time() - self.start
            print(f"  [{label}] done in {elapsed:.1f}s")

    return Timer()


def _get_channel_shops():
    """Return Shop queryset filtered by CHANNEL env var if set."""
    from django_pim.models import Shop

    if CHANNEL:
        return Shop.objects.filter(idx=CHANNEL)
    return Shop.objects.all()


def multiply_products(count: int) -> None:
    """Clone products from a template simple product."""
    shops = _get_channel_shops()
    if not shops.exists():
        print("ERROR: No shops found")
        return

    for shop in shops:
        template = ProductSimple.objects.filter(shop=shop).select_related("real_product").first()
        if not template:
            print(f"  No simple product in {shop.idx}, skipping")
            continue

        print(f"\n=== Multiplying {count} products in {shop.idx} ===")
        template_rp = template.real_product
        base_sku = template_rp.sku

        # Phase 1: RealProducts
        with _timer(f"RealProducts x{count}"):
            real_products = []
            for i in range(1, count + 1):
                rp = RealProduct(
                    sku=f"{base_sku}-MUL-{i:06d}",
                    weight=template_rp.weight,
                    ean=None,
                )
                real_products.append(rp)
            RealProduct.objects.bulk_create(real_products, batch_size=BATCH_SIZE, ignore_conflicts=True)

        # Re-query for PKs (bulk_create + ignore_conflicts doesn't return PKs on Postgres)
        with _timer("Re-query RealProduct PKs"):
            skus = [f"{base_sku}-MUL-{i:06d}" for i in range(1, count + 1)]
            rp_map = dict(RealProduct.objects.filter(sku__in=skus).values_list("sku", "pk"))

        # Phase 2: Product + ProductSimple (MTI — bulk parent, then bulk child)
        with _timer(f"Product (parent) x{count}"):
            products = []
            for i in range(1, count + 1):
                sku = f"{base_sku}-MUL-{i:06d}"
                if sku not in rp_map:
                    continue
                products.append(
                    Product(
                        shop=shop,
                        real_product_id=rp_map[sku],
                        feature_set=template.feature_set,
                        product_class=template.product_class,
                        visibility=template.visibility,
                        is_enabled=True,
                    )
                )
            Product.objects.bulk_create(products, batch_size=BATCH_SIZE, ignore_conflicts=True)

        # Re-query Product PKs
        with _timer("Re-query Product PKs"):
            product_map = dict(
                Product.objects.filter(
                    shop=shop,
                    real_product__sku__in=skus,
                ).values_list("real_product__sku", "pk")
            )

        # Insert ProductSimple child rows via raw SQL (Django forbids bulk_create on MTI)
        with _timer(f"ProductSimple (child) x{len(product_map)}"):
            pks = list(product_map.values())
            table = ProductSimple._meta.db_table
            for batch_start in range(0, len(pks), BATCH_SIZE):
                batch = pks[batch_start : batch_start + BATCH_SIZE]
                placeholders = ",".join(["(%s, 0)"] * len(batch))
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO {table} (product_ptr_id, quantity) VALUES {placeholders} ON CONFLICT DO NOTHING",
                        batch,
                    )

        # Phase 3: ProductAttributes (clone template's attributes)
        template_attrs = list(ProductAttribute.objects.filter(product=template))
        if template_attrs:
            with _timer(f"ProductAttributes x{len(template_attrs)}x{count}"):
                attrs = []
                for product_pk in product_map.values():
                    for ta in template_attrs:
                        attrs.append(
                            ProductAttribute(
                                product_id=product_pk,
                                feature=ta.feature,
                                attribute=ta.attribute,
                                value_bool=ta.value_bool,
                                value_decimal=ta.value_decimal,
                                value_datetime=ta.value_datetime,
                                value_txt=ta.value_txt,
                                value_txt_t9n=ta.value_txt_t9n,
                                value_json=ta.value_json,
                            )
                        )
                    if len(attrs) >= BATCH_SIZE:
                        ProductAttribute.objects.bulk_create(attrs, batch_size=BATCH_SIZE, ignore_conflicts=True)
                        attrs = []
                if attrs:
                    ProductAttribute.objects.bulk_create(attrs, batch_size=BATCH_SIZE, ignore_conflicts=True)

        # Phase 4: ProductInCategory (clone template's categories)
        template_cats = ProductInCategory.objects.filter(product=template)
        if template_cats.exists():
            with _timer(f"ProductInCategory x{len(template_cats)}x{count}"):
                pics = []
                for sku_key, product_pk in product_map.items():
                    for tc in template_cats:
                        pics.append(
                            ProductInCategory(
                                product_id=product_pk,
                                category=tc.category,
                            )
                        )
                    if len(pics) >= BATCH_SIZE:
                        ProductInCategory.objects.bulk_create(pics, batch_size=BATCH_SIZE, ignore_conflicts=True)
                        pics = []
                if pics:
                    ProductInCategory.objects.bulk_create(pics, batch_size=BATCH_SIZE, ignore_conflicts=True)

        total = Product.objects.filter(shop=shop).count()
        print(f"  Total products in {shop.idx}: {total}")


def multiply_categories(count: int) -> None:
    """Clone subtrees of the first L1 category with children."""
    shops = _get_channel_shops()
    if not shops.exists():
        print("ERROR: No shops found")
        return

    for shop in shops:
        # Find first L1 category that has children
        template = None
        l1_cats = ProductCategory.objects.filter(shop=shop, tree_deep=1).order_by("position")

        for cat in l1_cats:
            if ProductCategory.objects.filter(shop=shop, parent_category=cat).exists():
                template = cat
                break

        if not template:
            print(f"  No L1 category with children in {shop.idx}, skipping")
            continue

        print(f"\n=== Cloning {count} subtrees from '{template.idx}' in {shop.idx} ===")

        def _clone_subtree(source: ProductCategory, parent: ProductCategory | None, suffix: str) -> int:
            """Recursively clone a category and its children. Returns count created."""
            new_cat = ProductCategory(
                shop=shop,
                idx=f"{source.idx}-clone-{suffix}",
                parent_category=parent,
                name_t9n=source.name_t9n,
                description_t9n=source.description_t9n,
                url_key_t9n={k: f"{v}-clone-{suffix}" for k, v in (source.url_key_t9n or {}).items() if v},
                position=source.position,
                is_active=source.is_active,
                is_in_menu=source.is_in_menu,
            )
            new_cat.save()  # tree_deep computed in save()
            created = 1

            children = ProductCategory.objects.filter(shop=shop, parent_category=source).order_by("position")
            for child in children:
                created += _clone_subtree(child, new_cat, suffix)

            return created

        total_created = 0
        with _timer(f"Category subtrees x{count}"):
            root = ProductCategory.objects.filter(shop=shop, tree_deep=0).first()
            for i in range(1, count + 1):
                total_created += _clone_subtree(template, root, f"{i:04d}")

        total = ProductCategory.objects.filter(shop=shop).count()
        print(f"  Created {total_created} categories, total in {shop.idx}: {total}")


def multiply_feature_sets(count: int) -> None:
    """Clone a feature set with its feature links."""
    # Find first non-default feature set
    template = FeatureSet.objects.exclude(idx="default").first()
    if not template:
        print("ERROR: No non-default feature set found")
        return

    print(f"\n=== Cloning {count} feature sets from '{template.idx}' ===")
    template_links = FeatureInFeatureSet.objects.filter(feature_set=template)

    with _timer(f"FeatureSets x{count}"):
        for i in range(1, count + 1):
            new_idx = f"{template.idx}-clone-{i:04d}"
            if FeatureSet.objects.filter(idx=new_idx).exists():
                continue
            new_fs = FeatureSet(
                idx=new_idx,
                name=template.name,
                desc=template.desc,
            )
            new_fs.save()

            links = []
            for link in template_links:
                links.append(
                    FeatureInFeatureSet(
                        feature_set=new_fs,
                        feature=link.feature,
                        position=link.position,
                    )
                )
            FeatureInFeatureSet.objects.bulk_create(links, ignore_conflicts=True)

    total = FeatureSet.objects.count()
    print(f"  Total feature sets: {total}")


def multiply_attributes(count: int) -> None:
    """Generate attribute values for SELECT/MULTISELECT features."""
    select_types = [7, 8]  # SELECT, MULTISELECT
    features = Feature.objects.filter(feature_type__in=select_types)

    if not features.exists():
        print("ERROR: No SELECT/MULTISELECT features found")
        return

    print(f"\n=== Generating {count} attributes per feature ===")

    for feature in features:
        with _timer(f"Attributes for '{feature.idx}' x{count}"):
            for i in range(1, count + 1):
                attr = Attribute(
                    feature=feature,
                    idx=f"{feature.idx}-attr-{i:04d}",
                    name_t9n={"en": f"Variant {i:04d}", "pl": f"Wariant {i:04d}"},
                    display_order=1000 + i,
                )
                attr.save()  # save() validates idx + auto-generates magento_idx

        total = Attribute.objects.filter(feature=feature).count()
        print(f"  Total attributes for '{feature.idx}': {total}")


def _make_png(r: int, g: int, b: int) -> bytes:
    """Generate a minimal 1x1 PNG with the given RGB color. No Pillow needed."""

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8bit, RGB
    ihdr = _chunk(b"IHDR", ihdr_data)
    raw_row = bytes([0, r, g, b])  # filter byte + RGB
    idat = _chunk(b"IDAT", zlib.compress(raw_row))
    iend = _chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


def multiply_pictures(count: int) -> None:
    """Add many unique images to a single product."""
    if not SKU:
        print("ERROR: MULTIPLY_SKU is required for pictures")
        return

    channel = CHANNEL or "default-europe"
    product = Product.objects.filter(real_product__sku=SKU, shop__idx=channel).first()
    if not product:
        print(f"ERROR: Product {SKU} not found in channel {channel}")
        return

    print(f"\n=== Adding {count} pictures to {SKU} in {channel} ===")

    import tempfile

    with _timer(f"Pictures x{count}"):
        for i in range(1, count + 1):
            r = (i * 37) % 256
            g = (i * 73) % 256
            b = (i * 113) % 256
            png_bytes = _make_png(r, g, b)

            # HashedImageField.save calls magic.from_file(str(content)) where
            # str(content) = content.name — so name must be a real file path
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(png_bytes)
                tmp_path = tmp.name

            import hashlib as _hashlib

            with open(tmp_path, "rb") as f:
                sha1 = _hashlib.sha1(f.read()).hexdigest()
                f.seek(0)

                # Reuse existing Picture if SHA1 matches (idempotent)
                existing = Picture.objects.filter(sha1=sha1).first()
                if existing:
                    pic = existing
                else:
                    from django.core.files import File

                    pic = Picture(image=File(f, name=tmp_path))
                    pic.save()

            os.unlink(tmp_path)

            ProductPicture.objects.create(
                product=product,
                picture=pic,
                picture_role=2,  # GENERAL
                position=1000 + i,
            )

    total = ProductPicture.objects.filter(product=product).count()
    print(f"  Total pictures on {SKU}: {total}")


def multiply_links(count: int) -> None:
    """Add many product links to a single product."""
    if not SKU:
        print("ERROR: MULTIPLY_SKU is required for links")
        return

    channel = CHANNEL or "default-europe"
    product = Product.objects.filter(real_product__sku=SKU, shop__idx=channel).first()
    if not product:
        print(f"ERROR: Product {SKU} not found in channel {channel}")
        return

    link_type = ProductLinkType.objects.filter(idx="related").first()
    if not link_type:
        print("ERROR: 'related' link type not found")
        return

    # Get other products in same channel (excluding self)
    other_products = (
        Product.objects.filter(shop__idx=channel).exclude(pk=product.pk).values_list("pk", flat=True)[:count]
    )

    if not other_products:
        print("ERROR: No other products found to link. Run multiply-products first.")
        return

    actual_count = len(other_products)
    print(f"\n=== Adding {actual_count} links to {SKU} in {channel} ===")

    with _timer(f"ProductLinks x{actual_count}"):
        links = [
            ProductLink(
                product=product,
                linked_product_id=other_pk,
                link_type=link_type,
                position=i,
            )
            for i, other_pk in enumerate(other_products, start=1)
        ]
        ProductLink.objects.bulk_create(links, batch_size=BATCH_SIZE, ignore_conflicts=True)

    total = ProductLink.objects.filter(product=product).count()
    print(f"  Total links on {SKU}: {total}")


def multiply_all(count: int) -> None:
    """Run all multipliers in sequence."""
    multiply_products(count)
    multiply_categories(min(count // 20, 50) or 1)
    multiply_feature_sets(min(count // 10, 100) or 1)
    multiply_attributes(min(count // 2, 500) or 1)
    print("\n=== Skipping pictures and links in 'all' mode (require SKU) ===")


# --- Dispatch ---

DISPATCH = {
    "products": multiply_products,
    "categories": multiply_categories,
    "feature_sets": multiply_feature_sets,
    "attributes": multiply_attributes,
    "pictures": multiply_pictures,
    "links": multiply_links,
    "all": multiply_all,
}

print(f"\n{'=' * 60}")
print(f"Devtools Multiplier — entity={ENTITY} count={COUNT}")
if CHANNEL:
    print(f"  channel={CHANNEL}")
if SKU:
    print(f"  sku={SKU}")
print(f"{'=' * 60}")

handler = DISPATCH.get(ENTITY)
if not handler:
    print(f"ERROR: Unknown entity '{ENTITY}'. Choose from: {', '.join(DISPATCH)}")
    sys.exit(1)

start = time.time()
handler(COUNT)
elapsed = time.time() - start
print(f"\n{'=' * 60}")
print(f"Completed in {elapsed:.1f}s")
print(f"{'=' * 60}")
