# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CMS e2e fixtures. Shared constants/gating live in entirius_tests.cms_e2e."""

import pytest
from playwright.sync_api import Page, expect

from entirius_tests.ai_studio_e2e import AdminApi, service_api, toolbox_api, toolbox_has_seo
from entirius_tests.cms_e2e import ADMIN_PASSWORD, ADMIN_USERNAME, CMS_BASE_URL


@pytest.fixture
def admin_page(page: Page) -> Page:
    """A CMS page with the admin already logged in."""
    page.goto(f"{CMS_BASE_URL}/")
    page.get_by_role("textbox", name="Username").fill(ADMIN_USERNAME)
    page.get_by_role("textbox", name="Password").fill(ADMIN_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    # A goto right after the click would abort the login request.
    expect(page.get_by_role("button", name="Log in")).to_be_hidden(timeout=15000)
    return page


@pytest.fixture
def enrichment_api() -> AdminApi:
    """The service admin API (JWT) — setup and reset of the AI studio tests."""
    return service_api()


@pytest.fixture
def tracker_api() -> AdminApi:
    """The AI toolbox admin API (JWT) — its tracker usage records count the AI calls."""
    return toolbox_api()


@pytest.fixture(scope="session")
def toolbox_seo() -> bool:
    """The AI toolbox serves the SEO app; asked once per session, at test time (never at collection)."""
    return toolbox_has_seo()


@pytest.fixture
def require_toolbox_seo(toolbox_seo: bool) -> None:
    """Skips a test that needs the toolbox SEO app (`/api/ai-seo/`) while the toolbox has none."""
    if not toolbox_seo:
        pytest.skip("the AI toolbox has no SEO app (/api/ai-seo/) yet")
