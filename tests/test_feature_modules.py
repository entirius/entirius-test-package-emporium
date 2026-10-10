# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Feature -> munin module map (`required_modules`) and the module skips of the behave hooks."""

import importlib.util
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from conftest import REPO_ROOT

from entirius_tests.munin import required_modules

_spec = importlib.util.spec_from_file_location("behave_environment", REPO_ROOT / "features" / "environment.py")
environment = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(environment)

FEATURE_FILES = sorted(path.relative_to(REPO_ROOT).as_posix() for path in REPO_ROOT.glob("features/**/*.feature"))


def test_the_tree_has_feature_files():
    assert FEATURE_FILES


@pytest.mark.parametrize("path", FEATURE_FILES)
def test_every_feature_file_is_mapped(path):
    assert isinstance(required_modules(path), frozenset)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("features/lookup/lookup_check.feature", {"lookup", "atlas"}),
        ("features/access/security/token_abuse.feature", {"access"}),
        ("features/matrix_v2/products_search.feature", {"matrix"}),
        ("features/toolbox/toolbox_outage.feature", {"communicator"}),
        ("features/harness/mail_roundtrip.feature", set()),
        ("features/admin/pim_feature_sets_crud.feature", {"pim"}),
        ("features/admin/qms_warehouse_admin.feature", {"qms"}),
        ("/srv/features/clone/features/checkout/order_flow.feature", {"checkout"}),
    ],
)
def test_required_modules(path, expected):
    assert required_modules(path) == expected


@pytest.mark.parametrize("path", ["features/unknown/x.feature", "features/admin/unknown_admin.feature", "x.feature"])
def test_an_unmapped_feature_file_is_an_error(path):
    with pytest.raises(KeyError):
        required_modules(path)


def _run_before_feature(installed: set[str] | None, path: str, tags: tuple[str, ...] = ()) -> MagicMock:
    feature = MagicMock(filename=path, tags=list(tags))
    environment.before_feature(SimpleNamespace(installed_modules=installed), feature)
    return feature


def test_feature_of_an_absent_module_is_skipped_with_the_reason():
    feature = _run_before_feature({"lookup", "pim"}, "features/lookup/lookup_check.feature")
    feature.skip.assert_called_once_with(reason="module 'atlas' not installed (munin registry)")


def test_feature_with_an_absent_module_tag_is_skipped():
    feature = _run_before_feature({"pim"}, "features/admin/pim_admin.feature", tags=("admin", "suppliers"))
    feature.skip.assert_called_once_with(reason="module 'suppliers' not installed (munin registry)")


@pytest.mark.parametrize("installed", [{"lookup", "atlas"}, None])
def test_feature_runs_with_its_modules_or_without_a_registry(installed):
    _run_before_feature(installed, "features/lookup/lookup_check.feature").skip.assert_not_called()


def _run_before_scenario(installed: set[str] | None, tags: set[str]) -> MagicMock:
    context = SimpleNamespace(api=MagicMock(), toolbox_state=None, installed_modules=installed)
    scenario = MagicMock(effective_tags=tags)
    environment.before_scenario(context, scenario)
    return scenario


def test_scenario_tagged_with_an_absent_module_is_skipped():
    scenario = _run_before_scenario({"pim"}, {"v2", "module-qms"})
    scenario.skip.assert_called_once_with(reason="module 'qms' not installed (munin registry)")


@pytest.mark.parametrize("installed", [{"pim", "qms"}, None])
def test_scenario_runs_with_its_module_or_without_a_registry(installed):
    _run_before_scenario(installed, {"module-qms"}).skip.assert_not_called()
