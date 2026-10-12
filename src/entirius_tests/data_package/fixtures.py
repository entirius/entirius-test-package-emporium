# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The `fixtures/` directory: one channel (pk 1) per module, for an empty migrated database."""

from pathlib import Path

import yaml

from entirius_tests.data_package.csvs import QTY_FILE, TAX_CLASS
from entirius_tests.data_package.profile import Profile, regional_pk, regional_rows

FIXTURES_DIR = "fixtures"
QMS_FIXTURE = "django_qms.cfg.yaml"
FIXTURE_TIMESTAMP = "2025-01-01 00:00:00+00:00"  # the only date in a package: the same input gives the same bytes
CHANNEL_PK = 1


def _record(model: str, fields: dict, pk: int = CHANNEL_PK) -> dict:
    return {"model": model, "pk": pk, "fields": fields}


def _regional_keys(profile: Profile) -> dict:
    """The relations of a channel to django_regional, by the pks of the regional fixture."""
    languages = [regional_pk("language", language) for language in profile.languages]
    return {
        "default_language": regional_pk("language", profile.default_language),
        "default_currency": regional_pk("currency", profile.currency),
        "default_country": regional_pk("country", profile.default_country),
        "languages": languages,
        "currencies": [regional_pk("currency", profile.currency)],
        "countries": [regional_pk("country", profile.default_country)],
    }


def _translated(profile: Profile, text: str) -> dict:
    return dict.fromkeys(profile.languages, text)


def _regional(profile: Profile) -> list[dict]:
    """Languages only: the regional migration already creates the currencies and the countries."""
    return [regional_rows("language")[language] for language in profile.languages]


def _pim(profile: Profile) -> list[dict]:
    keys = _regional_keys(profile)
    fields = {"idx": profile.idx, "name": profile.name, "is_default": True}
    relations = ("default_language", "default_currency", "languages", "currencies")
    return [_record("django_pim.channel", fields | {key: keys[key] for key in relations})]


def _pricemanager(profile: Profile) -> list[dict]:
    country = regional_pk("country", profile.default_country)
    sale_channel = {
        "idx": profile.idx,
        "name": profile.name,
        "channel": CHANNEL_PK,
        "is_only_for_verified_user": False,
        "price_source": "csv",
        "country": country,
        "customer_representation": None,
    }
    return [
        _record("django_pricemanager.channel", {"idx": profile.idx, "name": profile.name, "calculate_direction": 1}),
        _record("django_pricemanager.salechannel", sale_channel),
        _record("django_pricemanager.taxclass", {"idx": TAX_CLASS, "name": "Standard Rate", "source_file": ""}),
        _record("django_pricemanager.taxrate", {"tax_class": 1, "country": country, "rate": profile.tax_rate}),
    ]


def _storages(profile: Profile, mount: str) -> list[dict]:
    """The quantity file as the input storage, the checkout stock as the output storage."""
    source = {
        "code": f"{profile.idx}-source-csv",
        "channel": CHANNEL_PK,
        "storage_manager": "csv",
        "data_direction": "input",
        "additional_data": {"csv_path": f"{mount}/{QTY_FILE}"},
    }
    target = {
        "code": f"{profile.idx}-target-checkout",
        "channel": CHANNEL_PK,
        "storage_manager": "checkout",
        "data_direction": "output",
        "additional_data": {},
    }
    return [_record("django_qms.xraystorage", source, pk=1), _record("django_qms.xraystorage", target, pk=2)]


def _qms(profile: Profile, mount: str) -> list[dict]:
    channel = {"idx": profile.idx, "name": f"{profile.name} QMS", "stock_weight": 1, "qms_type": "XRAY"}
    link = {"storage_input": 1, "storage_output": 2}
    return [
        _record("django_qms.channel", channel),
        *_storages(profile, mount),
        _record("django_qms.xraystoragelink", link),
    ]


def _checkout_channel(profile: Profile) -> dict:
    fields = {
        "idx": profile.idx,
        "label": profile.name,
        "discount_mode_of_action_price_restriction_type": "brutto",
        "order_pretty_id_prefix": None,
        "feature_idxs_for_split_order": "",
        "default_attr_split": "",
        "force_splitting_order_in_checkout": False,
        "split_order_shipping_cost_mechanism": "attribute_based_shipping_cost_assignment",
        "default_attr_split_shipping": "",
        "split_order_payment_fee_mechanism": "attribute_based_payment_fee_assignment",
        "default_attr_split_payment_fee": "",
        "min_order_price": 0,
        "discount_apply_type": "after",
        "split_order_mechanism": "CLOSE_AND_SPLIT",
    }
    return _record("django_checkout.channel", fields | _regional_keys(profile))


def _shipping_method(profile: Profile) -> dict:
    fields = {
        "channel": CHANNEL_PK,
        "method_type": "default",
        "code": "standard-shipping",
        "image": "",
        "name_t9n": _translated(profile, "Standard Shipping"),
        "description_t9n": None,
        "price_type": "fixed",
        "max_weight": None,
        "priority": 0,
    }
    return _record("django_checkout.shippingmethod", fields)


def _shipping_option(profile: Profile) -> dict:
    fields = {
        "method": 1,
        "country": regional_pk("country", profile.default_country),
        "country_code": profile.default_country,
        "currency": regional_pk("currency", profile.currency),
        "tax_rate": "0.00",
        "price_brutto": "9.99",
        "new_price": "0.00",
        "free_delivery_above_brutto": "200.00",
        "cash_on_delivery_available": False,
        "cash_on_delivery_fee": None,
    }
    return _record("django_checkout.shippingoption", fields)


def _payment(profile: Profile) -> dict:
    keys = _regional_keys(profile)
    fields = {
        "channel": CHANNEL_PK,
        "provider": "transfer",
        "code": "banktransfer",
        "is_cash_on_delivery": False,
        "is_free_order": False,
        "image": "",
        "name_t9n": _translated(profile, "Bank Transfer"),
        "description_t9n": None,
        "additional_data": None,
        "countries": keys["countries"],
        "currencies": keys["currencies"],
    }
    return _record("django_checkout.paymentmethod", fields)


def _checkout(profile: Profile) -> list[dict]:
    supplier = {"code": profile.idx, "name": profile.name, "is_global": True, "channel": CHANNEL_PK}
    return [
        _checkout_channel(profile),
        _shipping_method(profile),
        _shipping_option(profile),
        _record("django_checkout.supplier", supplier),
        _payment(profile),
    ]


def _matrix(profile: Profile) -> list[dict]:
    fields = {
        "created_at": FIXTURE_TIMESTAMP,
        "modified_at": FIXTURE_TIMESTAMP,
        "idx": profile.idx,
        "label": profile.idx,
        "default_order": "on_stock",
        "default_order_direction": "ASC",
    }
    return [_record("django_matrix.channel", fields | _regional_keys(profile))]


def _accounts(profile: Profile) -> list[dict]:
    language = regional_pk("language", profile.default_language)
    return [_record("django_accounts.channel", {"idx": profile.idx, "label": profile.name, "language": language})]


def write_fixtures(profile: Profile, out: Path, mount: str) -> list[str]:
    """Write the fixtures; returns the file names in load order."""
    fixtures = {
        "django_regional.cfg.yaml": _regional(profile),
        "django_pim.cfg.yaml": _pim(profile),
        "django_pricemanager.cfg.yaml": _pricemanager(profile),
        QMS_FIXTURE: _qms(profile, mount),
        "django_checkout.cfg.yaml": _checkout(profile),
        "django_matrix.cfg.yaml": _matrix(profile),
        "django_accounts.cfg.yaml": _accounts(profile),
    }
    (out / FIXTURES_DIR).mkdir()
    for name, records in fixtures.items():
        text = yaml.safe_dump(records, sort_keys=False, allow_unicode=True)
        (out / FIXTURES_DIR / name).write_text(text, encoding="utf-8")
    return list(fixtures)
