# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Host-side prep for the @suppliers-e2e BDD suite.

Run BEFORE behave via:
    docker compose exec -T volkanos python manage.py shell < .../seed-suppliers-e2e.py

Why this exists (and is not pure-HTTP): the suite needs supplier config that the admin
API schema does NOT expose (realproduct_match_tolerance_pct, preferred_switch_cooldown_hours,
preferred_switch_hysteresis_pct, eval_frequency) plus a pre-existing RealProduct carrying a
known EAN for the auto-link scenarios. The behave container has no docker socket, so this
ORM setup runs host-side. The feeds + feeds/mapping-profiles/attribute-mappings are still
created via the admin API inside the feature Backgrounds.

Idempotent: wipes prior bdd-* supplier products/links/feeds, then re-creates the preset
suppliers with knobs baked in, then stamps the anchor RealProduct.
"""

from decimal import Decimal

from django_regional.models import Currency, Language
from django_suppliers.enums import EvalFrequency, ReviewMode, SupplierType
from django_suppliers.models import (
    ProductSupplierLink,
    Supplier,
    SupplierFeed,
    SupplierMappingProfile,
    SupplierProduct,
)

# Dedicated anchor RealProduct with NO channel Product — so an EAN auto-link can create
# the channel Product fresh. A seeded product (already on every channel) would make
# init_push raise "Product already exists ... use force_repush".
ANCHOR_SKU = "BDD-EAN-ANCHOR"
ANCHOR_EAN = "5900000000017"
WAREHOUSE = "novatrade-wh"

# (idx, sku_prefix, default_language iso2) — knobs are identical preset for all.
# "novatrade" backs the physical-race/audit scenarios that address a named supplier
# directly; without it the suite depends on a supplier pre-existing in the environment.
PRESETS = [
    ("bdd-ult-sup", "BULT", "en"),
    ("bdd-sup-a", "BSA", "en"),
    ("bdd-sup-b", "BSB", "en"),
    ("bdd-sup-lang", "BLNG", "de"),  # default_language NOT in default-local[en] -> fallback
    ("novatrade", "NOVA", "en"),
]
SUPPLIER_IDXS = [p[0] for p in PRESETS]
# Generated RealProduct SKUs are `{sku_prefix}-{sha1(external_id)[:12]}`.
SKU_PREFIXES = [f"{p[1]}-" for p in PRESETS]


def _lang(iso2: str) -> Language:
    return Language.objects.get(iso2=iso2)


def _eur() -> Currency:
    return Currency.objects.get(iso3="EUR")


def _wipe_generated_pim_state() -> None:
    """Drop RealProducts (+ their channel products / prices / stock) that prior pushes
    generated under the bdd sku prefixes. Without this, the deterministic SKU collides:
    init_push refuses with 'Product already exists ... use force_repush'. The anchor
    ENT-C005 has no bdd prefix, so it survives."""
    from contextlib import suppress

    # QMS stock is keyed by plain sku string (no FK cascade) — purge explicitly.
    with suppress(Exception):
        from django_qms.models import WarehouseStock

        for pref in SKU_PREFIXES:
            WarehouseStock.objects.filter(sku__startswith=pref).delete()

    # Prices reference RealProduct via FK; delete first in case on_delete is PROTECT.
    with suppress(Exception):
        from django_pricemanager.models import CurrentPrice

        for pref in SKU_PREFIXES:
            CurrentPrice.objects.filter(product__sku__startswith=pref).delete()
    with suppress(Exception):
        from django_pricemanager.models import PriceHistory

        for pref in SKU_PREFIXES:
            PriceHistory.objects.filter(product__sku__startswith=pref).delete()

    # Channel Products protect/anchor the RealProduct and are what trigger
    # "Product already exists ... use force_repush" on re-push — drop them first.
    with suppress(Exception):
        from django_pim.models import Product

        for pref in SKU_PREFIXES:
            Product.objects.filter(real_product__sku__startswith=pref).delete()

    with suppress(Exception):
        from django_pim.models import RealProduct

        for pref in SKU_PREFIXES:
            RealProduct.objects.filter(sku__startswith=pref).delete()


def _wipe_prior_run() -> None:
    """Remove per-run artifacts so each suite run starts from a clean slate."""
    sups = list(Supplier.objects.filter(idx__in=SUPPLIER_IDXS))
    if sups:
        ProductSupplierLink.objects.filter(supplier__in=sups).delete()
        SupplierProduct.objects.filter(supplier__in=sups).delete()
        SupplierFeed.objects.filter(supplier__in=sups).delete()
        SupplierMappingProfile.objects.filter(supplier__in=sups).delete()
    _wipe_generated_pim_state()


def _upsert_suppliers() -> None:
    eur = _eur()
    for idx, prefix, lang_iso in PRESETS:
        Supplier.objects.update_or_create(
            idx=idx,
            defaults={
                "name": f"BDD E2E {idx}",
                "supplier_type": SupplierType.FEED,
                "review_mode": ReviewMode.MANUAL,
                "is_active": True,
                "default_language": _lang(lang_iso),
                "default_currency": eur,
                "sku_prefix": prefix,
                "target_warehouse_code": WAREHOUSE,
                "qty_subtract": 0,
                "qty_minimum": 0,
                # auto-preferred: kill cron + anti-flap guards so back-to-back deltas can flip
                "eval_frequency": EvalFrequency.MANUAL,
                "preferred_switch_cooldown_hours": 0,
                "preferred_switch_hysteresis_pct": 2,
                # EAN auto-link: default 10% tolerance (the EAN scenarios rely on this default)
                "realproduct_match_tolerance_pct": 10,
                "disable_ean_auto_link": False,
                "allow_physical_writes_from_non_preferred": False,
            },
        )


def _ensure_anchor() -> str:
    """Create/reset the channel-free anchor RealProduct for EAN auto-link.

    weight is compared raw against the SP's mapped grams (the grams_to_kg modifier is NOT
    applied to get_or_create defaults — only on write), so the anchor weight must equal
    ean_match.xml's weight_g (2000) for tolerance to pass. Its channel Product + links are
    dropped each run so the auto-linked push can recreate the Product cleanly."""
    from contextlib import suppress

    from django_pim.models import Product, RealProduct

    with suppress(Exception):
        Product.objects.filter(real_product__sku=ANCHOR_SKU).delete()
    ProductSupplierLink.objects.filter(real_product_sku=ANCHOR_SKU).delete()
    # Clear the EAN off any other product (e.g. an earlier ENT-C005 stamping) so the
    # anchor is the unique match for 5900000000017.
    with suppress(Exception):
        RealProduct.objects.filter(ean=ANCHOR_EAN).exclude(sku=ANCHOR_SKU).update(ean="")
    RealProduct.objects.update_or_create(sku=ANCHOR_SKU, defaults={"ean": ANCHOR_EAN, "weight": Decimal("2000.00")})
    return f"anchor {ANCHOR_SKU}: ready (ean={ANCHOR_EAN}, weight=2000, no channel product)"


def _ensure_warehouse() -> str:
    """The presets point target_warehouse_code at WAREHOUSE, but qms_writer does a hard
    `Warehouse.objects.get(code=...)` — on a fresh DB the warehouse does not exist and every
    stock write is silently skipped (e2e_01 then fails on 'warehouse not in stock rows').
    Create it here so the suite carries its own prerequisite."""
    from django_qms.models.warehouse import SourceType, Warehouse

    Warehouse.objects.update_or_create(
        code=WAREHOUSE,
        defaults={"name": "BDD E2E supplier warehouse", "source_type": SourceType.INTEGRATION, "is_active": True},
    )
    return f"warehouse {WAREHOUSE}: ready"


def main() -> None:
    _wipe_prior_run()
    _upsert_suppliers()
    anchor_msg = _ensure_anchor()
    warehouse_msg = _ensure_warehouse()
    print("=== seed-suppliers-e2e ===")
    print(f"suppliers ready: {', '.join(SUPPLIER_IDXS)}")
    print(anchor_msg)
    print(warehouse_msg)
    print("=== done ===")


main()
