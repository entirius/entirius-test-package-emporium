# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CMS e2e fixtures. Shared constants/gating live in entirius_tests.cms_e2e."""

import pytest
from playwright.sync_api import Page

from entirius_tests.cms_e2e import ADMIN_PASSWORD, ADMIN_USERNAME, CMS_BASE_URL


@pytest.fixture
def admin_page(page: Page) -> Page:
    """A CMS page with the admin already logged in."""
    page.goto(f"{CMS_BASE_URL}/")
    page.get_by_role("textbox", name="Username").fill(ADMIN_USERNAME)
    page.get_by_role("textbox", name="Password").fill(ADMIN_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    return page
