# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI toolbox state from the munin registry and the `@needs-toolbox` skip of `before_scenario`."""

import importlib.util
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from conftest import REPO_ROOT

from entirius_tests.munin import TOOLBOX_ABSENT, TOOLBOX_TAG, parse_toolbox_state

_spec = importlib.util.spec_from_file_location("behave_environment", REPO_ROOT / "features" / "environment.py")
environment = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(environment)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"platform": {"toolbox": {"state": "configured"}, "toolbox_status": "unreachable"}}, "configured"),
        ({"platform": {"toolbox": {"state": "disabled"}}}, "disabled"),
        ({"platform": {"toolbox": None, "toolbox_status": "configured"}}, TOOLBOX_ABSENT),
        ({"platform": {"toolbox_status": "unconfigured"}}, "unconfigured"),
        ({"platform": {"version": "1.0.0"}}, None),
        ({"platform": {"toolbox": {}}}, None),
        ({"platform": {"toolbox": "configured"}}, None),
        ({"platform": None}, None),
        ({}, None),
        ([], None),
    ],
)
def test_parse_toolbox_state(payload, expected):
    assert parse_toolbox_state(payload) == expected


def _run_before_scenario(state: str | None, tags: set[str]) -> MagicMock:
    context = SimpleNamespace(api=MagicMock(), toolbox_state=state)
    scenario = MagicMock(effective_tags=tags)
    environment.before_scenario(context, scenario)
    return scenario


@pytest.mark.parametrize("state", ["disabled", "unconfigured", "unreachable", TOOLBOX_ABSENT])
def test_tagged_scenario_is_skipped_with_the_state_as_reason(state):
    scenario = _run_before_scenario(state, {TOOLBOX_TAG, "leads"})
    scenario.skip.assert_called_once()
    assert f"AI toolbox {state}" in scenario.skip.call_args.kwargs["reason"]


@pytest.mark.parametrize("state", ["configured", None])
def test_tagged_scenario_runs_when_the_toolbox_answers_or_the_probe_failed(state):
    _run_before_scenario(state, {TOOLBOX_TAG}).skip.assert_not_called()


def test_untagged_scenario_is_never_skipped():
    _run_before_scenario("disabled", {"leads", "v2"}).skip.assert_not_called()
