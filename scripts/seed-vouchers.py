# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Seed voucher channel config + campaigns + product-vouchers for E2E/BDD tests.

Run from inside the volkanos container, AFTER the package import (products must
exist — ProductVoucher.product is a PROTECT FK to pim.Product). Wired into
entirius-docker-seed.sh Step 6, after `sync_voucher_channels`.

Why a Python seed (not a loaddata fixture): ProductVoucher / VoucherProductFilter
FK + M2M target pim.Product, which is CSV-imported (Step 4) AFTER fixtures load
(Step 2), and imported product PKs are not stable. Looking products up by the
stable SKU here sidesteps both problems. Individual Voucher rows are NOT seeded —
tests issue them at runtime via the admin API (codes are Fernet/HMAC, fresh
voucher per scenario = deterministic).

Idempotent: re-running updates config in place, never duplicates.
"""

import django

django.setup()

from decimal import Decimal

from django_checkout_voucher.models import Channel, ProductVoucher, VoucherCampaign
from django_checkout_voucher.models.enums import TaxType, VoucherCampaignType
from django_checkout_voucher.services import channel_service
from django_pim.models import Product
from django_regional.models import Currency

# Channel roles (idx must match seeded pim/checkout channels):
#   default-europe — primary happy-path channel (EUR), all defaults.
#   default-local  — require_pin variant (USD), for PIN / lockout tests.
PRIMARY_IDX = "default-europe"
PIN_IDX = "default-local"
PRIMARY_CURRENCY = "EUR"
PIN_CURRENCY = "USD"

# Anchor product for the voucher template (any seeded SKU; values are snapshotted
# at issue, the FK is lineage only for admin-issue / redemption tests).
ANCHOR_SKU = "ENT-S001"


def _channel(idx):
    return Channel.objects.get(idx=idx)


def _currency(iso3):
    return Currency.objects.get(iso3=iso3)


def _anchor_product(channel_idx):
    return Product.objects.filter(real_product__sku__iexact=ANCHOR_SKU, shop__idx=channel_idx).first()


def configure_channels():
    """Primary: no PIN, extension allowed (admin tooling tests). PIN channel: require_pin
    + issuance-approval gate.

    default-local carries require_issuance_approval=True so the approval gate is exercised
    E2E: buying the voucher-template product there mints the SALE voucher in PENDING_APPROVAL
    (held, no code email) until an admin approves (→ ACTIVE, PIN generated) or rejects
    (→ CANCELED). The gate only fires on SALE auto-issue — ADMIN_ISSUE (the PIN/lockout
    tests on this channel) is unaffected."""
    Channel.objects.filter(idx=PRIMARY_IDX).update(
        require_pin=False, require_issuance_approval=False, allow_extension=True
    )
    Channel.objects.filter(idx=PIN_IDX).update(require_pin=True, require_issuance_approval=True)
    print(f"Channels configured: {PRIMARY_IDX} (allow_extension), {PIN_IDX} (require_pin + approval gate)")


def seed_campaigns():
    """ADMIN_ISSUED + SALE on primary; ADMIN_ISSUED on the PIN channel."""
    specs = [
        (PRIMARY_IDX, VoucherCampaignType.ADMIN_ISSUED, "E2E Admin Issued (EUR)"),
        (PRIMARY_IDX, VoucherCampaignType.SALE, "E2E Sale (EUR)"),
        (PIN_IDX, VoucherCampaignType.ADMIN_ISSUED, "E2E Admin Issued PIN (USD)"),
        (PIN_IDX, VoucherCampaignType.SALE, "E2E Sale Approval (USD)"),
    ]
    for idx, typ, name in specs:
        VoucherCampaign.objects.get_or_create(
            name=name, channel=_channel(idx), defaults={"typ": typ, "is_active": True}
        )
        print(f"Campaign: {name} [{typ}] / {idx}")


def seed_product_vouchers():
    """MPV + SPV face-100 template on primary; MPV face-100 on the PIN channel."""
    specs = [
        (PRIMARY_IDX, PRIMARY_CURRENCY, TaxType.MPV),
        (PRIMARY_IDX, PRIMARY_CURRENCY, TaxType.SPV),
        (PIN_IDX, PIN_CURRENCY, TaxType.MPV),
    ]
    for idx, cur, tax in specs:
        product = _anchor_product(idx)
        if product is None:
            print(f"  [WARN] no product '{ANCHOR_SKU}' on channel {idx} — skipped ProductVoucher")
            continue
        ProductVoucher.objects.get_or_create(
            channel=_channel(idx),
            product=product,
            tax_type=tax,
            defaults={"face_value": Decimal("100.00"), "currency": _currency(cur), "is_active": True},
        )
        print(f"ProductVoucher: face 100 {cur} [{tax}] / {idx} (product {ANCHOR_SKU})")


def seed_voucher_payment_methods():
    """A PaymentMethod with provider='voucher' must exist per channel for redemption
    (PaymentMethod._get_provider_cls dispatches the voucher provider). Mirror the
    channel's existing transfer method's countries/currencies."""
    from django_checkout.models import Channel as CheckoutChannel
    from django_checkout.models import PaymentMethod

    for idx in (PRIMARY_IDX, PIN_IDX):
        channel = CheckoutChannel.objects.filter(idx=idx).first()
        if channel is None:
            continue
        template = PaymentMethod.objects.filter(channel=channel).exclude(provider="voucher").first()
        pm, created = PaymentMethod.objects.get_or_create(
            channel=channel,
            provider="voucher",
            code="voucher",
            defaults={"is_cash_on_delivery": False, "is_free_order": False, "name_t9n": {"en": "Gift card / Voucher"}},
        )
        if created and template is not None:
            pm.countries.set(template.countries.all())
            pm.currencies.set(template.currencies.all())
        print(f"PaymentMethod voucher / {idx} (created={created})")


def main():
    channel_service.sync_channels_from_pim()
    configure_channels()
    seed_campaigns()
    seed_product_vouchers()
    seed_voucher_payment_methods()
    print("\nVoucher seed summary:")
    for ch in Channel.objects.all().order_by("idx"):
        print(
            f"  {ch.idx}: require_pin={ch.require_pin} approval={ch.require_issuance_approval} "
            f"campaigns={ch.campaigns.count()} product_vouchers={ch.product_vouchers.count()}"
        )


main()
