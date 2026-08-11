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
MODULE_TAGS = frozenset({"atlas", "pricefighter", "suppliers"})


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
