# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Seed a manual Warehouse per channel with a few SKU rows.

Run from inside the volkanos container (via entirius-docker-seed.sh).

Lets QA test the CMS manual edit flow + signal propagation
(WarehouseStock change -> checkout.Stock update -> Matrix re-render).
The `main-{channel}` integration warehouses created by `backfill_warehouse`
mirror the authoritative qty.csv data and stay read-only in CMS — this
script adds `manual-{channel}` warehouses (source_type=manual) so operators
can demo the full edit loop without touching the integration data.
"""

import django

django.setup()

from django_checkout.models import Channel as CheckoutChannel
from django_qms.models import Channel as QmsChannel
from django_qms.models import SourceType, Warehouse, WarehouseStock
from django_qms.services import warehouse_service

# Small subset of real SKUs so testers can change qty in CMS and see the
# effect propagate to the storefront/Matrix immediately. Kept short to keep
# the manual warehouse visually distinct from the integration one.
#
# IMPORTANT: a manual-warehouse row with qty=0 zeroes that SKU's checkout.Stock
# (the warehouse->checkout signal makes the manual warehouse authoritative), so any
# SKU listed here becomes out-of-stock. Keep purchase-test-critical SKUs OUT of this
# list — notably the voucher-template ENT-S001 (SALE auto-issue / redemption tests buy
# it) and the cart product ENT-C002. Demo with non-critical SKUs only.
SEED_SKUS = ["ENT-C001", "ENT-C005", "ENT-S003", "ENT-B001"]

for ch in CheckoutChannel.objects.all():
    code = f"manual-{ch.idx}"
    warehouse, created = Warehouse.objects.get_or_create(
        code=code,
        defaults={
            "name": f"Manual stock ({ch.idx})",
            "source_type": SourceType.MANUAL,
            "is_active": True,
            "description": "Operator-managed stock. Edits propagate via signal to checkout.Stock.",
        },
    )
    qms_ch, _ = QmsChannel.objects.get_or_create(idx=ch.idx, defaults={"name": ch.idx})
    warehouse.channels.add(qms_ch)

    if created:
        items = [{"sku": sku, "quantity": 0} for sku in SEED_SKUS]
        warehouse_service.bulk_upsert_stock(warehouse, items, allow_integration=False)
        print(f"Created {code} with {len(items)} placeholder SKUs (qty=0, editable in CMS)")
    else:
        print(f"Skipped {code} (already exists)")

print(f"\nTotal warehouses: {Warehouse.objects.count()}")
for w in Warehouse.objects.filter(source_type=SourceType.MANUAL):
    stock_count = WarehouseStock.objects.filter(warehouse=w).count()
    print(f"  manual: {w.code} ({stock_count} stocks)")
