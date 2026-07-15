# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from dataclasses import dataclass, field

import requests


@dataclass
class ApiClient:
    """Thin HTTP client for Volkanos API.

    URL pattern: /api/{module}/v{version}/{channel}/...
    Response format: {"meta": {...}, "data": [...], "pagination": {...}}
    """

    base_url: str
    api_version: str = "1"
    session: requests.Session = field(default_factory=requests.Session)
    checkout_api_key: str = "entirius-docker-checkout-dev-key-2026"

    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def matrix_url(self, channel: str, path: str = "") -> str:
        base = f"{self.base_url}/api/matrix/v{self.api_version}/{channel}"
        if path:
            return f"{base}/{path.lstrip('/')}"
        return f"{base}/"

    def contentdb_url(self, path: str = "") -> str:
        base = f"{self.base_url}/api/contentdb/v{self.api_version}"
        if path:
            return f"{base}/{path.lstrip('/')}"
        return f"{base}/"

    def checkout_url(self, channel: str, path: str = "") -> str:
        base = f"{self.base_url}/api/checkout/v{self.api_version}/{channel}"
        if path:
            return f"{base}/{path.lstrip('/')}"
        return f"{base}/"

    def _headers_for(self, url: str) -> dict[str, str]:
        """Return extra headers based on the URL (e.g. API key for checkout)."""
        if "/api/checkout/" in url and self.checkout_api_key:
            return {"X-API-KEY": self.checkout_api_key}
        return {}

    def get(self, url: str, **kwargs: object) -> requests.Response:
        headers = {**self._headers_for(url), **kwargs.pop("headers", {})}
        return self.session.get(url, timeout=30, headers=headers, **kwargs)

    def post(self, url: str, **kwargs: object) -> requests.Response:
        headers = {**self._headers_for(url), **kwargs.pop("headers", {})}
        return self.session.post(url, timeout=30, headers=headers, **kwargs)

    def put(self, url: str, **kwargs: object) -> requests.Response:
        headers = {**self._headers_for(url), **kwargs.pop("headers", {})}
        return self.session.put(url, timeout=30, headers=headers, **kwargs)

    def patch(self, url: str, **kwargs: object) -> requests.Response:
        headers = {**self._headers_for(url), **kwargs.pop("headers", {})}
        return self.session.patch(url, timeout=30, headers=headers, **kwargs)

    def delete(self, url: str, **kwargs: object) -> requests.Response:
        headers = {**self._headers_for(url), **kwargs.pop("headers", {})}
        return self.session.delete(url, timeout=30, headers=headers, **kwargs)

    def set_auth_token(self, token: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_auth_token(self) -> None:
        self.session.headers.pop("Authorization", None)
