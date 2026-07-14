# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import requests


def obtain_jwt_token(base_url: str, username: str, password: str) -> str:
    """Obtain JWT access token from the Volkanos API.

    Uses the standard simplejwt token endpoint at /api/token/.
    """
    response = requests.post(
        f"{base_url}/api/token/",
        json={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access"]
