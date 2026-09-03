# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The CSV product-count step treats the CSV as a floor, not an exact match.

Anything else that seeds products into the channel (the suppliers e2e preset)
adds rows the CSV never mentions; an equality check fails on a correct system.
"""

from pathlib import Path
from types import SimpleNamespace

import api_steps
import pytest

from entirius_tests.csv_loader import load_products

CHANNEL = "default-europe"
PACKAGE_PATH = str(Path(__file__).resolve().parents[1] / "package")


def _csv_product_count():
    return len(load_products(PACKAGE_PATH, CHANNEL))


def _context(item_count):
    """A behave context whose API response carries `item_count` products."""
    items = [{"sku": f"ENT-S{i:03d}"} for i in range(item_count)]
    response = SimpleNamespace(json=lambda: {"meta": {}, "data": items})
    return SimpleNamespace(response=response, test_package_path=PACKAGE_PATH, channel=CHANNEL)


def test_csv_count_accepts_more_products_than_the_csv():
    api_steps.step_count_at_least_csv(_context(_csv_product_count() + 1))


def test_csv_count_accepts_exactly_the_csv_count():
    api_steps.step_count_at_least_csv(_context(_csv_product_count()))


def test_csv_count_rejects_fewer_products_than_the_csv():
    with pytest.raises(AssertionError):
        api_steps.step_count_at_least_csv(_context(_csv_product_count() - 1))
