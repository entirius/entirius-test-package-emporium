# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Value steps behind the matrix v2 search scenarios.

They pin what the search scenarios claim: a narrowed result list, a `total` that
counts matches rather than echoing the page size, and a `meta.status` string.
"""

from types import SimpleNamespace

import matrix_v2_steps
import pytest

SEARCH_PAGE = {
    "meta": {"status": "ok", "warnings": []},
    "products": {
        "total": 7,
        "has_next_page": True,
        "results": [{"sku": "ENT-S001"}, {"sku": "ENT-S004"}],
    },
}


def _context(data):
    return SimpleNamespace(response_data=data)


def test_key_is_true_accepts_a_boolean_true():
    matrix_v2_steps.step_key_is_true(_context(SEARCH_PAGE), "products.has_next_page")


def test_key_is_true_rejects_a_truthy_string():
    data = {"products": {"has_next_page": "true"}}
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_key_is_true(_context(data), "products.has_next_page")


def test_key_at_least_accepts_the_boundary_value():
    matrix_v2_steps.step_key_at_least(_context(SEARCH_PAGE), "products.total", 7)


def test_key_at_least_rejects_a_value_below_the_floor():
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_key_at_least(_context({"products": {"total": 0}}), "products.total", 1)


def test_key_has_at_least_accepts_a_populated_result_list():
    matrix_v2_steps.step_key_has_at_least(_context(SEARCH_PAGE), "products.results", 1)


def test_key_has_at_least_rejects_an_empty_result_list():
    """A search term that matches nothing must fail the narrowing scenarios."""
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_key_has_at_least(_context({"products": {"results": []}}), "products.results", 1)


def test_key_greater_than_len_accepts_a_total_above_the_page():
    matrix_v2_steps.step_key_greater_than_len(_context(SEARCH_PAGE), "products.total", "products.results")


def test_key_greater_than_len_rejects_a_total_that_echoes_the_page_size():
    data = {"products": {"total": 2, "results": [{"sku": "ENT-S001"}, {"sku": "ENT-S004"}]}}
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_key_greater_than_len(_context(data), "products.total", "products.results")


def test_dotted_is_str_accepts_the_matching_meta_status():
    matrix_v2_steps.step_dotted_is_str(_context(SEARCH_PAGE), "meta.status", "ok")


def test_dotted_is_str_rejects_a_different_meta_status():
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_dotted_is_str(_context(SEARCH_PAGE), "meta.status", "warning")
