# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Atlas operator workload (seed.sh Step 6x, AFTER execute_source_feed).

Run via:
    docker exec -i <service> python manage.py shell < scripts/seed-atlas-workload.py

Shapes the freshly-imported atl-nova products into a realistic operator state:

  ATL-N001..N003  approve + push -> 2 auto-matched RealProducts (EAN anchors),
                  1 physical_tolerance_violation event + fresh per-source RP
  ATL-N004        approve + push, then data_changed_at bumped past pushed_at
                  -> appears in the CMS "Updated" tab
  ATL-N005..N009  queued  -> the Swipe review queue (N009 is out of stock)
  ATL-N012        rejected
  ATL-N010, N011  left at `new`

Then seeds monitoring/enrichment observations for ATLAS UI variety (flags:
untrusted source, stock 0, stale ts). The pricefighter engine observations with
calibrated prices live in seed-pricefighter-e2e.py — SKU sets stay disjoint.

Idempotent: status transitions tolerate re-runs (already-correct statuses are
skipped); pushes run only for still-approved products; observations for the
touched SKUs are wiped and re-recorded.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_atlas.enums import ProductStatus
from django_atlas.models import Observation, Source, SourceProduct
from django_atlas.services import push_service, review_service
from django_atlas.services.observation_service import record_observation

NOVA_IDX = "atl-nova"
PUSH_TARGETS = ["ATL-N001", "ATL-N002", "ATL-N003", "ATL-N004"]
QUEUE_TARGETS = ["ATL-N005", "ATL-N006", "ATL-N007", "ATL-N008", "ATL-N009"]
REJECT_TARGETS = ["ATL-N012"]
UPDATED_TARGET = "ATL-N004"

# Atlas-UI-only observation variety (pricefighter's calibrated ones are separate).
OBSERVED_SKUS = ["ENT-S001", "ENT-S002"]


def _sp(source, external_id):
    return SourceProduct.objects.get(source=source, external_id=external_id)


def _admin():
    return User.objects.filter(is_superuser=True).order_by("id").first()


def _transition(source, external_ids, target, admin):
    done = 0
    for ext in external_ids:
        sp = _sp(source, ext)
        if sp.status == target:
            continue
        review_service.transition_status(sp, target, user=admin)
        done += 1
    return done


def _push(source):
    if not SourceProduct.objects.filter(source=source, status=ProductStatus.APPROVED).exists():
        return "push: nothing approved (already pushed?)"
    counts = push_service.push_approved_for_source(source.id, user=None)
    return f"push: success={counts.get('success', 0)} failed={counts.get('failed', 0)}"


def _push_warehouse_event():
    """Push BDD-ATL-P003 (atl-push, no target warehouse) so the Events feed carries a
    deterministic qms_warehouse_not_configured warning right after seed. P001/P002 stay
    approved — they are reserved for the @atlas push BDD scenarios."""
    from django.db import transaction

    push_source = Source.objects.get(idx="atl-push")
    sp = SourceProduct.objects.get(source=push_source, external_id="BDD-ATL-P003")
    if sp.status != ProductStatus.APPROVED:
        return f"warehouse-event push: BDD-ATL-P003 is {sp.status}, skipped"
    with transaction.atomic():
        push_service.push_source_product(sp.id, None)
    return "warehouse-event push: BDD-ATL-P003 pushed (qms_warehouse_not_configured emitted)"


def _bump_updated(source):
    sp = _sp(source, UPDATED_TARGET)
    if not sp.pushed_at:
        return f"updated-bump: {UPDATED_TARGET} not pushed, skipped"
    SourceProduct.objects.filter(pk=sp.pk).update(data_changed_at=sp.pushed_at + timedelta(hours=1))
    return f"updated-bump: {UPDATED_TARGET} data_changed_at > pushed_at"


def _seed_observations():
    now = timezone.now()
    de = Source.objects.get(idx="atl-watch-de")
    pl = Source.objects.get(idx="atl-watch-pl")
    sig = Source.objects.get(idx="atl-signals")

    eu = Source.objects.get(idx="atl-watch-eu")
    Observation.objects.filter(source__in=[de, pl, sig, eu], sku__in=OBSERVED_SKUS).delete()

    # ENT-S001 flags as the DE-market detail actually renders them (latest per source;
    # sources scoped to a different country are dropped entirely):
    #   atl-watch-de -> latest row is out-of-stock (the earlier 899 is hidden),
    #   atl-watch-eu -> PLN price on a EUR market = currency_mismatch,
    #   atl-watch-pl -> visible only on the PL market row (untrusted flag there).
    record_observation(source=de, sku="ENT-S001", value={"price": "899.00", "currency": "EUR", "stock": 4})
    record_observation(source=pl, sku="ENT-S001", value={"price": "3599.00", "currency": "PLN", "stock": 9})
    record_observation(source=de, sku="ENT-S001", value={"price": "879.00", "currency": "EUR", "stock": 0})
    record_observation(source=eu, sku="ENT-S001", value={"price": "3499.00", "currency": "PLN", "stock": 7})
    # ENT-S002: only a stale observation (outside the pricefighter staleness window).
    record_observation(
        source=de,
        sku="ENT-S002",
        value={"price": "1499.00", "currency": "EUR", "stock": 2},
        ts=now - timedelta(days=10),
    )
    # Enrichment signals for the atl-signals source.
    record_observation(source=sig, sku="ENT-S001", value={"signals": {"rating": 4.6, "reviews": 132}})
    record_observation(source=sig, sku="ENT-S002", value={"signals": {"rating": 4.1, "reviews": 47}})
    return f"observations: {Observation.objects.filter(source__in=[de, pl, sig]).count()} rows"


def main():
    admin = _admin()
    nova = Source.objects.get(idx=NOVA_IDX)
    approved = _transition(nova, PUSH_TARGETS, ProductStatus.APPROVED, admin)
    queued = _transition(nova, QUEUE_TARGETS, ProductStatus.QUEUED, admin)
    rejected = _transition(nova, REJECT_TARGETS, ProductStatus.REJECTED, admin)
    push_msg = _push(nova)
    event_msg = _push_warehouse_event()
    updated_msg = _bump_updated(nova)
    obs_msg = _seed_observations()

    from django.db.models import Count

    counts = dict(
        SourceProduct.objects.filter(source=nova).values_list("status").annotate(n=Count("id")).values_list("status", "n")
    )
    print("=== seed-atlas-workload ===")
    print(f"transitions: approved={approved} queued={queued} rejected={rejected}")
    print(push_msg)
    print(event_msg)
    print(updated_msg)
    print(obs_msg)
    print(f"atl-nova statuses: {counts}")
    print("=== done ===")


main()
