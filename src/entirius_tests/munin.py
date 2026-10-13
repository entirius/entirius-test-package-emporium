# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared munin module-registry contract for the test suites.

Both behave (features/environment.py) and pytest e2e import from here so a
registry path/shape change is fixed in one place.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePath

MUNIN_REGISTRY_PATH = "api/munin/v2/"

# Feature/module tags that map 1:1 onto munin module keys. A feature carrying one
# of these tags is skipped when the backend does not report the module — the
# suite stays green against environments that adopted fewer modules.
MODULE_TAGS = frozenset({"atlas", "pricefighter", "suppliers", "leads", "communicator", "siteintel", "notifications"})

# A scenario tag `@module-<key>` names one more munin module that scenario needs.
MODULE_TAG_PREFIX = "module-"

# Modules the registry never lists. A tag that names one is decided by a registered module standing in for it:
# omnibus by pricemanager (it needs its prices); reviews and vault by checkout, a convention of the suite and
# not a rule of the registry (a stack that enables them without checkout skips their scenarios).
UNREGISTERED_MODULES = {"omnibus": "pricemanager", "reviews": "checkout", "vault": "checkout"}

# Feature directory -> the munin module keys its features need. A feature is skipped when the
# backend does not report one of them, so the suite runs against any module subset. An empty set
# is harness plumbing: no module. `features/admin/` is mapped per file, see ADMIN_FEATURE_PREFIXES.
_SAME_NAME = (
    "access",
    "agreements",
    "atlas",
    "checkout",
    "communicator",
    "contact_forms",
    "contentdb",
    "deliverypoints",
    "faq",
    "leads",
    "matrix",
    "notifications",
    "pim_csv",
    "pricemanager",
    "qms",
    "siteintel",
    "suppliers",
)
FEATURE_MODULES: dict[str, frozenset[str]] = {
    **{name: frozenset({name}) for name in _SAME_NAME},
    "matrix_v2": frozenset({"matrix"}),
    "lookup": frozenset({"lookup", "atlas"}),
    "pricefighter": frozenset({"pricefighter", "atlas"}),
    "toolbox": frozenset({"communicator"}),
    "harness": frozenset(),
}

# `features/admin/<prefix>_*.feature` needs the module `<prefix>`.
ADMIN_FEATURE_PREFIXES = frozenset(
    {
        "accounts",
        "agreements",
        "contentdb",
        "deliverypoints",
        "email",
        "faq",
        "pim",
        "pricemanager",
        "qms",
        "regional",
        "suppliers",
    }
)

# A scenario carrying this tag needs a live AI completion. It runs when the registry reports the toolbox
# as `configured` (or the probe failed) and is skipped with a reason for every other state.
TOOLBOX_TAG = "needs-toolbox"
TOOLBOX_READY_STATE = "configured"
TOOLBOX_ABSENT = "absent"


def parse_modules(payload: dict) -> set[str] | None:
    """Module keys from a munin registry response body.

    Returns None for an empty or unshaped registry — an empty `modules` dict on
    a live backend means a broken discovery scan, not "nothing installed", and
    must not silently skip every module-tagged feature.
    """
    modules = payload.get("modules") if isinstance(payload, dict) else None
    if not isinstance(modules, dict) or not modules:
        return None
    return set(modules.keys())


def parse_toolbox_state(payload: dict) -> str | None:
    """AI toolbox state from a munin registry response body (`platform.toolbox.state`).

    `platform.toolbox` null means the toolbox client is not installed ("absent"). A registry without the
    `toolbox` key is an older munin: its deprecated `platform.toolbox_status` is read instead. Returns None
    for an unshaped payload or when neither field is there — an unknown state must not skip anything.
    """
    platform = payload.get("platform") if isinstance(payload, dict) else None
    if not isinstance(platform, dict):
        return None
    if "toolbox" not in platform:
        return platform.get("toolbox_status")
    toolbox = platform["toolbox"]
    if toolbox is None:
        return TOOLBOX_ABSENT
    return toolbox.get("state") if isinstance(toolbox, dict) else None


def required_modules(path: str) -> frozenset[str]:
    """Munin module keys a feature file needs, from its place under `features/`.

    Raises KeyError for a file the map does not cover: a new feature directory (or admin file
    prefix) is added to the map together with its features.
    """
    parts = PurePath(path).parts
    if "features" not in parts[:-1]:
        raise KeyError(path)
    section = parts[len(parts) - 1 - parts[-2::-1].index("features")]
    if section != "admin":
        return FEATURE_MODULES[section]
    prefix = parts[-1].split("_", 1)[0]
    if prefix not in ADMIN_FEATURE_PREFIXES:
        raise KeyError(path)
    return frozenset({prefix})


def tagged_modules(tags: Iterable[str]) -> set[str]:
    """Registry keys the `@module-<key>` tags need; an unregistered module is read through its stand-in."""
    keys = (tag.removeprefix(MODULE_TAG_PREFIX) for tag in tags if tag.startswith(MODULE_TAG_PREFIX))
    return {UNREGISTERED_MODULES.get(key, key) for key in keys}


def missing_module(required: frozenset[str] | set[str], installed: set[str] | None) -> str | None:
    """The first required module key the registry does not list; None when all are there or the
    registry could not tell (`installed` is None: nothing is skipped)."""
    if installed is None:
        return None
    return next((key for key in sorted(required) if key not in installed), None)
