# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Atlas prep on the freshly-reset DB (seed.sh Step 3d).

Run via:
    docker exec -i <service> python manage.py shell < scripts/seed-atlas-e2e.py

Creates everything the atlas pipeline phase (Step 6x) and the @atlas BDD suite
need but cannot create through the admin API alone:

- EAN anchor RealProducts (channel-Product-free, so init push can auto-link and
  create the channel Product fresh) — weights stored RAW in grams, because the
  tolerance check compares un-modified mapped values (grams_to_kg applies only
  on write, mirroring the suppliers anchor precedent).
- Duplicate RealProduct pairs sharing an EAN: one pair within the 10% weight
  tolerance (suggestion `merge`), one with a missing weight (suggestion `review`).
- Sources: atl-nova (procurement + xml feed from the fixtures container),
  atl-push (procurement, FEED-LESS — owns every BDD push scenario, nothing ever
  delists its products), atl-watch-de / atl-watch-pl (monitoring; PL untrusted),
  atl-signals (enrichment).
- QMS warehouse for atl-nova; atl-push keeps target_warehouse_code empty on
  purpose (seeds a realistic qms_warehouse_not_configured event on push).
- Approved BDD-ATL-P00x SourceProducts on atl-push for the push scenarios.

Idempotent: wipes prior atlas artifacts (sources by idx, generated PIM state by
SKU prefix) before recreating. Addresses everything by natural key, never PK.

NOTE for standalone re-runs (outside seed.sh): the wipe removes ALL observations
of the atl-* sources — including the pricefighter-calibrated ones. Re-run
seed-atlas-workload.py AND seed-pricefighter-e2e.py afterwards to restore the
full workload.
"""

from contextlib import suppress
from decimal import Decimal

from django_atlas.enums import ProductStatus, ReviewMode, SourceKind, SourceType, SyncMode
from django_atlas.models import (
    Source,
    SourceAttributeMapping,
    SourceFeed,
    SourceMappingProfile,
    SourceProduct,
    SourceProductLink,
)
from django_atlas.models.source_attribute_mapping import AttributeMappingTargetType
from django_regional.models import Country, Currency, Language

FEED_URL = "http://fixtures:8000/package/source-feeds/atlas-nova-v1.xml"
TARGET_CHANNEL = "default-europe"  # carries pl+pln; the mandated push target
FEATURE_SET = "furniture"  # existing PIM FeatureSet (same one suppliers use)
WAREHOUSE = "atlas-wh"

NOVA_IDX = "atl-nova"
PUSH_IDX = "atl-push"
SOURCE_IDXS = [NOVA_IDX, PUSH_IDX, "atl-watch-de", "atl-watch-pl", "atl-watch-eu", "atl-signals"]
# Generated RealProduct SKUs are "{sku_prefix}-{sha1(external_id)[:12]}".
SKU_PREFIXES = ["ATL-", "ATLP-"]

# (sku, ean, weight grams) — weights must line up with atlas-nova-v1.xml weight_g:
#   ANCHOR-1 vs ATL-N001 1500g (equal), ANCHOR-2 vs ATL-N002 820g (2.4% < 10%),
#   ANCHOR-3 vs ATL-N003 5000g (80% -> physical_tolerance_violation).
ANCHORS = [
    ("ATL-ANCHOR-1", "5902000000011", Decimal("1500.00")),
    ("ATL-ANCHOR-2", "5902000000028", Decimal("800.00")),
    ("ATL-ANCHOR-3", "5902000000035", Decimal("1000.00")),
]
# (sku, ean, weight|None) — pairs share an EAN; weights drive the merge/review suggestion.
DUPLICATES = [
    ("ATL-DUP-A1", "5902000000905", Decimal("1000.00")),
    ("ATL-DUP-A2", "5902000000905", Decimal("1050.00")),  # 5% apart -> merge
    ("ATL-DUP-B1", "5902000000912", Decimal("1000.00")),
    ("ATL-DUP-B2", "5902000000912", None),  # missing weight -> review
]
PUSH_PRODUCTS = ["BDD-ATL-P001", "BDD-ATL-P002", "BDD-ATL-P003"]


def _lang(iso2):
    return Language.objects.get(iso2=iso2)


def _cur(iso3):
    return Currency.objects.get(iso3=iso3)


def _country(iso2):
    country = Country.objects.filter(iso2__iexact=iso2).first()
    if country is None:
        raise RuntimeError(f"regional Country {iso2!r} missing — fixtures not loaded?")
    return country


def _wipe_generated_pim_state():
    """Drop RealProducts (+ channel products / prices / stock) from prior pushes —
    a stale channel Product makes init_push raise 'Product already exists'."""
    with suppress(Exception):
        from django_qms.models import WarehouseStock

        for pref in SKU_PREFIXES:
            WarehouseStock.objects.filter(sku__startswith=pref).delete()
    with suppress(Exception):
        from django_pricemanager.models import CurrentPrice, PriceHistory

        for pref in SKU_PREFIXES:
            CurrentPrice.objects.filter(product__sku__startswith=pref).delete()
            PriceHistory.objects.filter(product__sku__startswith=pref).delete()
    with suppress(Exception):
        from django_pim.models import Product, RealProduct

        for pref in SKU_PREFIXES:
            Product.objects.filter(real_product__sku__startswith=pref).delete()
            RealProduct.objects.filter(sku__startswith=pref).delete()


def _wipe_prior_run():
    sources = list(Source.objects.filter(idx__in=SOURCE_IDXS))
    if sources:
        SourceProductLink.objects.filter(source__in=sources).delete()
        SourceProduct.objects.filter(source__in=sources).delete()
        SourceFeed.objects.filter(source__in=sources).delete()
        SourceMappingProfile.objects.filter(source__in=sources).delete()
    with suppress(Exception):
        from django_atlas.models import Observation

        # Observation.save() forbids updates (append-only) — delete is fine.
        Observation.objects.filter(source__idx__in=SOURCE_IDXS).delete()
    _wipe_generated_pim_state()


def _ensure_realproducts():
    from django_pim.models import Product, RealProduct

    for sku, ean, weight in ANCHORS + DUPLICATES:
        with suppress(Exception):
            Product.objects.filter(real_product__sku=sku).delete()
        # The anchor must be the unique holder of its EAN (duplicates pairs excepted).
        RealProduct.objects.filter(ean=ean).exclude(
            sku__in=[s for s, e, _ in ANCHORS + DUPLICATES if e == ean]
        ).update(ean=None)
        RealProduct.objects.update_or_create(sku=sku, defaults={"ean": ean, "weight": weight})
    return f"realproducts: {len(ANCHORS)} anchors, {len(DUPLICATES)} duplicate rows"


def _common_source_defaults(kind, lang="en", cur="EUR"):
    return {
        "kind": kind,
        "source_type": SourceType.FEED,
        "review_mode": ReviewMode.MANUAL,
        "is_active": True,
        "is_trusted": True,
        "default_language": _lang(lang),
        "default_currency": _cur(cur),
        "qty_subtract": 0,
        "qty_minimum": 0,
        "realproduct_match_tolerance_pct": 10,
        "disable_ean_auto_link": False,
    }


def _ensure_nova():
    source, _ = Source.objects.update_or_create(
        idx=NOVA_IDX,
        defaults={
            **_common_source_defaults(SourceKind.PROCUREMENT),
            "name": "NovaTrade Atlas",
            "sku_prefix": "ATL",
            "default_feature_set_idx": FEATURE_SET,
            "target_warehouse_code": WAREHOUSE,
        },
    )
    SourceFeed.objects.update_or_create(
        source=source,
        idx="main",
        defaults={
            "connector_kind": "xml_feed",
            "sync_mode": SyncMode.FULL,
            "is_active": True,
            "feed_config": {
                "feed_url": FEED_URL,
                "product_xpath": ".//product",
                "field_mapping": {
                    "external_id": "./sku/text()",
                    "name": "./name/text()",
                    "cost": "./price/text()",
                    "currency": "./price/@currency",
                    "stock": "./stock/text()",
                    "ean": "./ean/text()",
                    "url": "./url/text()",
                    "weight_g": "./weight_g/text()",
                    "category": "./category/text()",
                    "description": "./description/text()",
                },
            },
        },
    )
    profile, _ = SourceMappingProfile.objects.update_or_create(
        source=source,
        idx="default-eu",
        defaults={
            "name": "Default Europe",
            "target_channel_idxs": [TARGET_CHANNEL],
            "is_active": True,
            "import_language": _lang("en"),
        },
    )
    # weight_g -> RealProduct.weight: makes the EAN tolerance check compare real
    # values (no real_product mappings would mean nothing is compared at all).
    SourceAttributeMapping.objects.update_or_create(
        profile=profile,
        source_field="weight_g",
        defaults={
            "target_type": AttributeMappingTargetType.REAL_PRODUCT,
            "target_identifier": "weight",
            "modifier": "grams_to_kg",
        },
    )
    return f"{NOVA_IDX}: feed main -> {FEED_URL}, profile default-eu -> {TARGET_CHANNEL}"


def _ensure_push_source():
    from django.contrib.auth.models import User
    from django.utils import timezone

    source, _ = Source.objects.update_or_create(
        idx=PUSH_IDX,
        defaults={
            **_common_source_defaults(SourceKind.PROCUREMENT),
            "name": "BDD Atlas Push Source",
            "sku_prefix": "ATLP",
            "default_feature_set_idx": FEATURE_SET,
            # Empty on purpose: every push emits qms_warehouse_not_configured,
            # seeding a realistic warning into the Events feed.
            "target_warehouse_code": "",
        },
    )
    SourceMappingProfile.objects.update_or_create(
        source=source,
        idx="default-eu",
        defaults={
            "name": "Default Europe",
            "target_channel_idxs": [TARGET_CHANNEL],
            "is_active": True,
            "import_language": _lang("en"),
        },
    )
    admin = User.objects.filter(is_superuser=True).order_by("id").first()
    now = timezone.now()
    for external_id in PUSH_PRODUCTS:
        SourceProduct.objects.update_or_create(
            source=source,
            external_id=external_id,
            defaults={
                "feed": None,
                "name": f"{external_id} push product",
                "cost": Decimal("100.0000"),
                "currency": "EUR",
                "stock": 10,
                "ean": "",  # no EAN -> no auto-link; plain fresh RealProduct per push
                "image_urls": [],
                "data": {"category": "furniture/office"},
                "status": ProductStatus.APPROVED,
                "pushed_to_channel_idxs": [],
                "pushed_by": None,
                "pushed_at": None,
                "real_product": None,
                "reviewed_by": admin,
                "reviewed_at": now,
            },
        )
    return f"{PUSH_IDX}: {len(PUSH_PRODUCTS)} approved SPs (feed-less, no warehouse)"


def _ensure_watchers():
    Source.objects.update_or_create(
        idx="atl-watch-de",
        defaults={
            **_common_source_defaults(SourceKind.MONITORING),
            "name": "PriceWatch DE",
            "sku_prefix": "AWDE",
            "country": _country("de"),
        },
    )
    untrusted = _common_source_defaults(SourceKind.MONITORING)
    untrusted["is_trusted"] = False
    Source.objects.update_or_create(
        idx="atl-watch-pl",
        defaults={
            **untrusted,
            "name": "PriceWatch PL (untrusted)",
            "sku_prefix": "AWPL",
            "country": _country("pl"),
            "default_currency": _cur("PLN"),
        },
    )
    # Country-less watcher: its observations are valid on EVERY market of the
    # matching currency (pricefighter drops only different-non-null countries).
    Source.objects.update_or_create(
        idx="atl-watch-eu",
        defaults={
            **_common_source_defaults(SourceKind.MONITORING),
            "name": "PriceWatch EU (global)",
            "sku_prefix": "AWEU",
        },
    )
    Source.objects.update_or_create(
        idx="atl-signals",
        defaults={
            **_common_source_defaults(SourceKind.ENRICHMENT),
            "name": "Signal Feed",
            "sku_prefix": "ASIG",
        },
    )
    return "watchers: atl-watch-de (trusted), atl-watch-pl (untrusted), atl-watch-eu (global), atl-signals (enrichment)"


def _ensure_warehouse():
    from django_qms.models.warehouse import SourceType as WhSourceType
    from django_qms.models.warehouse import Warehouse

    Warehouse.objects.update_or_create(
        code=WAREHOUSE,
        defaults={"name": "Atlas E2E warehouse", "source_type": WhSourceType.INTEGRATION, "is_active": True},
    )
    return f"warehouse {WAREHOUSE}: ready"


def main():
    _wipe_prior_run()
    msgs = [
        _ensure_realproducts(),
        _ensure_nova(),
        _ensure_push_source(),
        _ensure_watchers(),
        _ensure_warehouse(),
    ]
    print("=== seed-atlas-e2e ===")
    for msg in msgs:
        print(msg)
    print("=== done ===")


main()
