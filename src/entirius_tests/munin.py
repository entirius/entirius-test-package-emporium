# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared munin module-registry contract for the test suites.

Both behave (features/environment.py) and pytest e2e import from here so a
registry path/shape change is fixed in one place.
"""

from __future__ import annotations

MUNIN_REGISTRY_PATH = "api/munin/v2/"

# Feature/module tags that map 1:1 onto munin module keys. A feature carrying one
# of these tags is skipped when the backend does not report the module — the
# suite stays green against environments that adopted fewer modules.
MODULE_TAGS = frozenset({"atlas", "pricefighter", "suppliers", "leads", "communicator", "siteintel", "notifications"})

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
