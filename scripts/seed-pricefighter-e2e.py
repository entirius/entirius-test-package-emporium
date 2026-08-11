# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PriceFighter operator workload (seed.sh Step 6y, AFTER sync commands).

Run via:
    docker exec -i <service> python manage.py shell < scripts/seed-pricefighter-e2e.py

The decision queue is COMPUTED, not stored — this script seeds the inputs that
make the engine emit every recommendation type on the default-europe/DE/EUR
market (tax 19%, baseline = net_cost * 1.20 * 1.19):

  sku       gross   cost   baseline   R(obs)  rule            -> recommendation
  ENT-C001  549     380    542.64      500    channel compete -> compete (T=498), obs
                                                                 from the GLOBAL watcher
                                                                 so every EUR market gets
                                                                 a row (multi-market demo)
  ENT-C002  319     220    314.16      289    channel compete -> compete (T=287)
  ENT-D001  999     650    928.20     1100    category raise  -> raise   (T=1098)
  ENT-O001  269     210    299.88      240    sku price_war   -> hold_at_floor
                                              (MAP 259 vs margin floor 262.40 -> 262.40)
  ENT-O002  359     250    357.00      355    channel compete -> hold (in_band)
  ENT-B001  1379    (none) —          1300    channel compete -> no_recommendation:no_cost
  ENT-C003  829     560    799.68      760    channel compete -> compete, APPLIED in-seed
  ENT-X001  1999    1300  1856.40     1800    channel compete -> applied at floor (MAP 1900),
                                              then observations invalidated -> the next
                                              apply is a revert_baseline CLAMPED to MAP

History after seed: ENT-C003 applied, ENT-X001 applied, ENT-X001 clamped revert.
ENT-C001 on the FR market gets CurrentPrice.source='admin_edit' — staged for the
BDD/operator "apply refused on admin-locked price" scenario (never applied here).

Idempotent: costs/configs/rules are update_or_create'd; observations for the
touched skus are wiped and re-recorded; re-running applies is a no-op (the
recomputed suggestion equals the already-written price -> stale/not_actionable).
"""

from decimal import Decimal

from django_atlas.models import Observation, Source
from django_atlas.services.observation_service import record_observation
from django_pricefighter.models import Channel as PfChannel
from django_pricefighter.models import PricingRule, QuoteConfig
from django_pricefighter.models import ProductRepresentation as PfRep
from django_pricefighter.services import apply_service, decision_view_service
from django_pricemanager.models import (
    BaselineConfig,
    CurrentPrice,
    PriceBoundsConfig,
    PurchaseCost,
)
from django_pricemanager.models import (
    Channel as PmChannel,
)
from django_pricemanager.models import (
    ProductRepresentation as PmRep,
)
from django_regional.models import Country, Currency

CHANNEL = "default-europe"
COUNTRY = "DE"
CURRENCY = "EUR"

# sku -> net purchase cost (ENT-B001 deliberately absent -> no_recommendation:no_cost)
COSTS = {
    "ENT-C001": Decimal("380.00"),
    "ENT-C002": Decimal("220.00"),
    "ENT-D001": Decimal("650.00"),
    "ENT-O001": Decimal("210.00"),
    "ENT-O002": Decimal("250.00"),
    "ENT-C003": Decimal("560.00"),
    "ENT-X001": Decimal("1300.00"),
}
# sku -> (source_idx, observed price) — atl-watch-eu is country-less (valid on
# every EUR market), atl-watch-de scopes the rest to the DE market only.
OBSERVATIONS = {
    "ENT-C001": ("atl-watch-eu", "500.00"),
    "ENT-C002": ("atl-watch-de", "289.00"),
    "ENT-D001": ("atl-watch-de", "1100.00"),
    "ENT-O001": ("atl-watch-de", "240.00"),
    "ENT-O002": ("atl-watch-de", "355.00"),
    "ENT-B001": ("atl-watch-de", "1300.00"),
    "ENT-C003": ("atl-watch-de", "760.00"),
    "ENT-X001": ("atl-watch-de", "1800.00"),
}
SEEDED_SKUS = sorted(OBSERVATIONS)


def _ensure_costs():
    channel = PmChannel.objects.get(idx=CHANNEL)
    country = Country.objects.get(iso2__iexact=COUNTRY)
    currency = Currency.objects.get(iso3=CURRENCY)
    for sku, net_cost in COSTS.items():
        PurchaseCost.objects.update_or_create(
            product=PmRep.objects.get(sku=sku),
            channel=channel,
            defaults={"country": country, "currency": currency, "net_cost": net_cost},
        )
    return f"purchase costs: {len(COSTS)}"


def _ensure_configs():
    channel = PmChannel.objects.get(idx=CHANNEL)
    BaselineConfig.objects.update_or_create(channel=channel, defaults={"markup_percent": Decimal("0.20")})
    # Global min-margin floor; loaddata would bypass clean(), ORM here runs it.
    global_bounds = PriceBoundsConfig.objects.filter(product__isnull=True, channel__isnull=True).first()
    if global_bounds:
        global_bounds.min_margin_percent = Decimal("0.05")
        global_bounds.map_value = None
        global_bounds.save()
    else:
        PriceBoundsConfig.objects.create(product=None, channel=None, min_margin_percent=Decimal("0.05"))
    # MAPs: O001 (price-war floor interplay), X001 (revert clamps to MAP).
    for sku, map_value in (("ENT-O001", "259.00"), ("ENT-X001", "1900.00")):
        PriceBoundsConfig.objects.update_or_create(
            product=PmRep.objects.get(sku=sku), channel=None, defaults={"map_value": Decimal(map_value)}
        )
    cfg, created = QuoteConfig.objects.get_or_create(
        currency=CURRENCY,
        range_from=Decimal("0"),
        range_to=None,
        defaults={
            "band_dn": Decimal("5.00"),
            "band_up": Decimal("5.00"),
            "undercut": Decimal("2.00"),
            "headroom": Decimal("2.00"),
            "max_step": Decimal("150.00"),
            "rounding": "none",
        },
    )
    cfg.full_clean()  # loaddata-style silent invalid configs are the #1 footgun
    return f"baseline+bounds+quote config ready (quote {'created' if created else 'kept'})"


def _ensure_rules():
    # ENT-D001 sits in `desks` and `standing-desks` at the same category position;
    # representation sync tie-breaks nondeterministically. Pin the denormalized
    # category so the `desks` raise rule always matches.
    PfRep.objects.filter(sku="ENT-D001", channel__idx=CHANNEL).update(category="desks")
    pf_channel = PfChannel.objects.get(idx=CHANNEL)
    PricingRule.objects.update_or_create(
        channel=pf_channel, sku=None, category_idx=None, defaults={"strategy": "compete", "mode": "suggestion"}
    )
    PricingRule.objects.update_or_create(
        category_idx="desks", sku=None, channel=None, defaults={"strategy": "raise", "mode": "suggestion"}
    )
    PricingRule.objects.update_or_create(
        sku="ENT-O001",
        category_idx=None,
        channel=None,
        defaults={"strategy": "compete", "mode": "suggestion", "price_war": True},
    )
    return f"rules: {PricingRule.objects.count()} (channel compete, desks raise, ENT-O001 price-war)"


def _record(sku, source_idx, price, **kwargs):
    record_observation(
        source=Source.objects.get(idx=source_idx),
        sku=sku,
        value={"price": price, "currency": CURRENCY, "stock": 5},
        **kwargs,
    )


def _seed_observations():
    Observation.objects.filter(sku__in=SEEDED_SKUS).delete()
    for sku, (source_idx, price) in OBSERVATIONS.items():
        _record(sku, source_idx, price)
    return f"observations: {len(OBSERVATIONS)}"


def _suggested(sku):
    rows, _ = decision_view_service.build_decision_rows(skus=[sku])
    for row in rows:
        d = row.decision
        if d.channel_idx == CHANNEL and d.country == COUNTRY and d.currency == CURRENCY:
            return d
    return None


def _apply(sku):
    decision = _suggested(sku)
    if decision is None or decision.suggested_price is None:
        return f"apply {sku}: nothing actionable ({decision.recommendation if decision else 'no row'})"
    result = apply_service.apply_single(
        apply_service.ApplyItem(
            sku=sku,
            channel_idx=CHANNEL,
            country=COUNTRY,
            currency=CURRENCY,
            expected_new_price=decision.suggested_price,
        )
    )
    return f"apply {sku}: {result.bucket} ({decision.recommendation} -> {decision.suggested_price})"


def _invalidate_x001_observations():
    """Flip ENT-X001's fresh observation to a PLN source -> currency_mismatch, so the
    sku stays a candidate but has zero VALID prices. With CurrentPrice.source now
    'pricefighter' (step above) the engine recommends revert_baseline."""
    Observation.objects.filter(sku="ENT-X001").delete()
    record_observation(
        source=Source.objects.get(idx="atl-watch-pl"),
        sku="ENT-X001",
        value={"price": "7900.00", "currency": "PLN", "stock": 3},
    )
    return "ENT-X001 observations invalidated (untrusted PLN watcher only)"


def _stage_admin_lock():
    """FR market of ENT-C001: admin-owned price. The pricefighter guard refuses to
    overwrite admin_edit -> the staged BDD/operator apply lands in `skipped`."""
    updated = CurrentPrice.objects.filter(
        product__sku="ENT-C001", channel__idx=CHANNEL, country__iso2__iexact="FR", currency__iso3=CURRENCY
    ).update(source="admin_edit")
    return f"admin lock on ENT-C001/FR: {updated} row(s)"


def main():
    msgs = [
        _ensure_costs(),
        _ensure_configs(),
        _ensure_rules(),
        _seed_observations(),
        _apply("ENT-C003"),
        _apply("ENT-X001"),
    ]
    msgs.append(_invalidate_x001_observations())
    msgs.append(_apply("ENT-X001"))  # revert_baseline, clamped to MAP by the guard
    msgs.append(_stage_admin_lock())

    rows, total = decision_view_service.build_decision_rows()
    recs = {}
    for row in rows:
        recs[row.decision.recommendation] = recs.get(row.decision.recommendation, 0) + 1
    print("=== seed-pricefighter-e2e ===")
    for msg in msgs:
        print(msg)
    print(f"decision rows: {total}, recommendations: {recs}")
    print("=== done ===")


main()
