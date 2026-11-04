# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""scripts/import-package.sh --dry-run: which steps a set of enabled apps runs."""

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "import-package.sh"
PIM_ONLY = "django_regional django_utils django_pim django_agreements django_email django_accounts"


def _plan(apps: str) -> list[str]:
    result = subprocess.run(
        ["/bin/bash", str(SCRIPT), "--dry-run"],
        env={"SEED_APPS": apps, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def test_thumbnails_skip_without_the_product_import():
    """PIM without PIM CSV (the website recipe) imports no pictures, so there is nothing to resize."""
    assert "seed: plan import 7c Thumbnails skip (django_pim_csv not enabled)" in _plan(PIM_ONLY)


def test_thumbnails_run_after_the_product_import():
    plan = _plan(f"{PIM_ONLY} django_pim_csv")
    assert "seed: plan import 5 Products run" in plan
    assert "seed: plan import 7c Thumbnails run" in plan
