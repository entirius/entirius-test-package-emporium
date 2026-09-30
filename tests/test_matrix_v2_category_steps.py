# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Collection steps behind the matrix v2 categories scenarios.

`categories/` answers with a bare tree list, but the batch `url_key` form answers
with a `{"results": []}` envelope — one feature file mixes both shapes.
"""

from types import SimpleNamespace

import matrix_v2_steps
import pytest

CATEGORY_TREE = [
    {"url_key": "sofas", "has_children": True, "children": [{"url_key": "sofa-beds"}]},
    {"url_key": "bedroom", "has_children": False, "children": []},
]

SOFA_SUBTREE = [
    {"url_key": "living-room-sofas", "has_children": False, "children": []},
    {"url_key": "sofa-beds", "has_children": False, "children": []},
]

BATCH_ENVELOPE = {"results": [{"url_key": "sofas"}, {"url_key": "bedroom"}]}


def _context(data):
    return SimpleNamespace(response_data=data)


def test_collection_contains_finds_an_item_in_a_bare_tree_list():
    matrix_v2_steps.step_collection_contains(_context(SOFA_SUBTREE), "url_key", "sofa-beds")


def test_collection_contains_finds_an_item_in_a_results_envelope():
    matrix_v2_steps.step_collection_contains(_context(BATCH_ENVELOPE), "url_key", "sofas")


def test_collection_contains_rejects_a_url_key_outside_the_subtree():
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_collection_contains(_context(SOFA_SUBTREE), "url_key", "bedroom")


def test_collection_contains_rejects_a_response_that_is_neither_shape():
    """The shape guard must reject, not degrade to an empty collection.

    Matching the message matters: an `_items` that returned [] for an unrecognised
    payload would still raise here, but for the wrong reason.
    """
    with pytest.raises(AssertionError, match="not a list nor"):
        matrix_v2_steps.step_collection_contains(_context({"detail": "Not found"}), "url_key", "sofas")


def test_each_item_has_key_accepts_a_tree_that_carries_has_children():
    matrix_v2_steps.step_each_item_has_key(_context(CATEGORY_TREE), "has_children")


def test_each_item_has_key_rejects_a_node_without_has_children():
    tree = [{"url_key": "sofas", "has_children": True}, {"url_key": "bedroom"}]
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_each_item_has_key(_context(tree), "has_children")


def test_each_item_has_key_rejects_an_empty_collection():
    """An empty tree must fail loudly instead of passing vacuously."""
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_each_item_has_key(_context([]), "has_children")


def test_each_item_empty_list_accepts_depth_truncated_children():
    matrix_v2_steps.step_each_item_empty_list(_context(SOFA_SUBTREE), "children")


def test_each_item_empty_list_rejects_children_that_were_not_truncated():
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_each_item_empty_list(_context(CATEGORY_TREE), "children")


def test_each_item_empty_list_rejects_a_dropped_children_key():
    """depth=1 truncates the subtree; dropping the key entirely is a contract break."""
    with pytest.raises(AssertionError):
        matrix_v2_steps.step_each_item_empty_list(_context([{"url_key": "sofa-beds"}]), "children")


def test_each_item_empty_list_rejects_an_empty_collection():
    """A subtree that came back empty must fail loudly instead of passing vacuously."""
    with pytest.raises(AssertionError, match="empty"):
        matrix_v2_steps.step_each_item_empty_list(_context([]), "children")
