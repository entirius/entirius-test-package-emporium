# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Make the behave step modules importable.

`features/steps/` is a plain directory loaded by behave at runtime, not a package,
so pytest cannot import the step modules without putting it on the path first.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT / "features" / "steps"))
