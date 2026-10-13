# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""`python -m entirius_tests.data_package build|validate`."""

import sys

from entirius_tests.data_package.cli import main

sys.exit(main())
