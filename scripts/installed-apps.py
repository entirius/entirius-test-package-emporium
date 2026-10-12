# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Print the label of every enabled Django app, one per line.

Run from the service directory (seed.sh and import-package.sh feed it on stdin):
    python - < scripts/installed-apps.py
A boot error exits non-zero: a service that does not start is never read as "module absent".
"""

import contextlib
import os
import sys


def main() -> None:
    sys.path.insert(0, os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
    import django
    from django.apps import apps

    with contextlib.redirect_stdout(sys.stderr):  # settings may print; stdout carries labels only
        django.setup()
    print("\n".join(config.label for config in apps.get_app_configs()))


main()
