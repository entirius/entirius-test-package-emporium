# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio in the CMS, the "lost user" paths: every AI screen on a desktop (1280 × 800) and on a phone (390 × 844).

For each screen the operator must be able to get there from the side menu (the phone: the menu, then the panel's
tab bar: Enrichment Review, Studio, Settings — runs and the setup screens are tabs of Review and Settings) or from the
product's AI drawer, see where they are (a title), see a way back or onwards, read an empty
state that says what to do next, and reload or share the URL without losing the screen. The layout checks: no
horizontal page scroll on a phone and no floating label of a toolbar select overlapping another control.
Read-only: no AI call, nothing created; the drawer's empty state comes from a product with nothing pending.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from playwright.sync_api import Locator, Page, expect

from entirius_tests import ai_studio_e2e as studio
from entirius_tests import ai_studio_pages as pages
from entirius_tests.cms_e2e import CMS_BASE_URL, require_module

pytestmark = [require_module("enrichment"), pytest.mark.desktop_only]

VIEWPORTS = {"desktop": {"width": 1280, "height": 800}, "phone": {"width": 390, "height": 844}}
PANEL = "Enricher"
EMPTY_SKU = "ENT-S001"
NO_HITS = "zz-no-such-subject-e2e"
GONE_ID = "999999999"
SETTLE_MS = 400

# A floating label and a control whose boxes intersect, as [label, control, label top, control bottom]; with a modal
# drawer open only what it holds counts (the page under the backdrop is out of reach).
_OVERLAPS_JS = """() => {
  const root = document.querySelector('[role="dialog"][aria-modal="true"]') || document;
  const seen = (el) => el.offsetParent !== null;
  const hit = (a, b) => a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5;
  const labels = [...root.querySelectorAll('.basic-select__floating')].filter(seen);
  const controls = [...root.querySelectorAll('input, button, textarea, .basic-select__control')].filter(seen);
  const found = [];
  for (const label of labels) {
    const box = label.getBoundingClientRect();
    for (const control of controls) {
      if (control.closest('.basic-select') === label.closest('.basic-select')) continue;
      const other = control.getBoundingClientRect();
      if (other.width && hit(box, other)) found.push([label.innerText, control.outerHTML.slice(0, 80), box.top, other.bottom]);
    }
  }
  return found;
}"""


@dataclass(frozen=True)
class Screen:
    """One AI screen: its deep link, its title, how an operator reaches it and what its "way on" is."""

    key: str
    path: str
    title: re.Pattern[str]
    reach: Callable[[Page, bool], None]
    onwards: Callable[[Page, bool], Locator]


# --- how an operator gets there --------------------------------------------------------------------------------------


def _sidebar(page: Page) -> Locator:
    return page.get_by_test_id("app-sidebar")


def _tab_bar(page: Page) -> Locator:
    return page.locator("[data-fid='tab-bar']")


def _open_panel(page: Page, phone: bool) -> None:
    """Home → the Enricher panel: the sidebar group on a desktop, the menu's panel link on a phone."""
    page.goto(f"{CMS_BASE_URL}/")
    if phone:
        page.get_by_role("button", name="Menu", exact=True).click()
        page.get_by_role("link", name=PANEL, exact=True).click()
        expect(page).to_have_url(re.compile(r"/enrichment(\?.*)?$"))
        return
    group = _sidebar(page).get_by_role("button", name=PANEL, exact=True)
    if group.get_attribute("aria-expanded") != "true":
        group.click()


def _entry_name(label: str) -> re.Pattern[str]:
    """A nav entry by its label; an entry's count badge sits after it (sidebar) or before it (phone tab bar)."""
    return re.compile(rf"^\d*\s*{re.escape(label)}\s*\d*$")


def _via_menu(label: str) -> Callable[[Page, bool], None]:
    """The panel's entry: the sidebar link on a desktop, the tab bar on a phone."""

    def reach(page: Page, phone: bool) -> None:
        _open_panel(page, phone)
        nav = _tab_bar(page) if phone else _sidebar(page)
        nav.get_by_role("link", name=_entry_name(label)).click()

    return reach


def _via_tab(entry: str, tab: str) -> Callable[[Page, bool], None]:
    """A tab of a panel entry: Review → Runs, Settings → Memory …"""

    def reach(page: Page, phone: bool) -> None:
        _via_menu(entry)(page, phone)
        page.get_by_test_id(f"enrichment-tab-{tab}").click()

    return reach


def _open_drawer(page: Page, phone: bool) -> None:
    """PIM → Products → the product → its AI drawer."""
    page.goto(f"{CMS_BASE_URL}/pim/products/{EMPTY_SKU}")
    pages.open_drawer(page)


def _history(page: Page, phone: bool) -> None:
    _via_tab("Settings", "profile")(page, phone)
    page.get_by_test_id("profile-history-open").click()


def _studio_run(page: Page, phone: bool) -> None:
    _via_menu("Studio")(page, phone)
    rows = page.get_by_test_id("runs-table").locator("[data-testid^='run-row-']")
    expect(rows.first).to_be_visible()
    rows.first.click()
    page.wait_for_url(re.compile(r"/enrichment/studio/[0-9a-f]+"))


# --- what shows the way on -------------------------------------------------------------------------------------------


def _lit_entry(page: Page, phone: bool) -> Locator:
    """A list screen of the panel: its entry lit in the tab bar (phone, always "page") or the sidebar (desktop:
    "page" on the entry's own address, "true" on its tabs — Review → Runs, every Settings tab)."""
    if phone:
        return _tab_bar(page).locator("[aria-current='page']")
    return _sidebar(page).locator("[aria-current]")


def _back(page: Page, phone: bool) -> Locator:
    return page.get_by_role("main").get_by_role("button", name="Back", exact=True)


def _drawer_close(page: Page, phone: bool) -> Locator:
    return page.get_by_test_id("side-drawer-close")


REVIEW = re.compile(r"^Enrichment Review$")
SETTINGS = re.compile(r"^Settings$")
SCREENS = [
    Screen("review", "/enrichment", REVIEW, _via_menu("Enrichment Review"), _lit_entry),
    Screen("runs", "/enrichment/runs", REVIEW, _via_tab("Enrichment Review", "runs"), _lit_entry),
    Screen("templates", "/enrichment/settings/templates", SETTINGS, _via_tab("Settings", "templates"), _lit_entry),
    Screen("profile", "/enrichment/settings/profile", SETTINGS, _via_tab("Settings", "profile"), _lit_entry),
    Screen("history", "/enrichment/settings/profile?history=1", re.compile(r"^History"), _history, _drawer_close),
    Screen("memory", "/enrichment/settings/memory", SETTINGS, _via_tab("Settings", "memory"), _lit_entry),
    Screen("studio", "/enrichment/studio", re.compile(r"^Studio$"), _via_menu("Studio"), _lit_entry),
    Screen("studio-run", "", re.compile(r"\S"), _studio_run, _back),
    Screen(
        "drawer",
        f"/pim/products/{EMPTY_SKU}?ai=1",
        re.compile(rf"^AI for (?!{EMPTY_SKU}$).+$"),
        _open_drawer,
        _drawer_close,
    ),
]
DRAWERS = {"history", "drawer"}


def _title(page: Page, screen: Screen) -> Locator:
    """The page's H1, or the open drawer's title."""
    if screen.key in DRAWERS:
        return page.get_by_role("dialog").get_by_role("heading", level=2)
    return page.get_by_role("heading", level=1)


def _assert_layout(page: Page, phone: bool) -> None:
    page.wait_for_timeout(SETTLE_MS)
    if phone:
        width = page.evaluate("document.documentElement.scrollWidth")
        assert width <= VIEWPORTS["phone"]["width"], f"the page scrolls sideways: {width} px"
    overlaps = page.evaluate(_OVERLAPS_JS)
    assert not overlaps, f"floating labels overlap other controls: {overlaps}"


@pytest.fixture
def nothing_pending(enrichment_api: studio.AdminApi) -> str:
    """The drawer's product with nothing waiting: its empty state shows."""
    studio.reject_pending(enrichment_api, EMPTY_SKU)
    return EMPTY_SKU


@pytest.mark.parametrize("viewport", list(VIEWPORTS))
@pytest.mark.parametrize("screen", SCREENS, ids=[screen.key for screen in SCREENS])
def test_screen_is_reachable_titled_and_reloadable(
    admin_page: Page, viewport: str, screen: Screen, nothing_pending: str
):
    page = admin_page
    phone = viewport == "phone"
    page.set_viewport_size(VIEWPORTS[viewport])

    screen.reach(page, phone)
    title = _title(page, screen)
    expect(title).to_have_text(screen.title)
    expect(screen.onwards(page, phone).first).to_be_in_viewport()
    _assert_layout(page, phone)

    shown = title.inner_text()
    page.reload()
    expect(_title(page, screen)).to_have_text(shown)
    expect(screen.onwards(page, phone).first).to_be_in_viewport()


def _goto(page: Page, viewport: str, path: str) -> None:
    page.set_viewport_size(VIEWPORTS[viewport])
    page.goto(f"{CMS_BASE_URL}{path}")


@pytest.mark.parametrize("viewport", list(VIEWPORTS))
def test_empty_states_say_what_to_do(admin_page: Page, viewport: str, nothing_pending: str):
    page = admin_page
    phone = viewport == "phone"

    _goto(page, viewport, f"/enrichment?task={GONE_ID}")
    empty = page.get_by_test_id("review-empty")
    expect(empty).to_be_visible()
    expect(page.get_by_test_id("review-empty")).to_have_count(1)
    expect(empty.get_by_test_id("review-empty-clear")).to_be_visible()
    expect(empty.get_by_test_id("review-empty-applied")).to_be_visible()
    expect(page.get_by_test_id("enrichment-task-filter-link")).to_have_text("AI task")
    _assert_layout(page, phone)
    empty.get_by_test_id("review-empty-clear").click()
    expect(page).not_to_have_url(re.compile(r"task="))

    _goto(page, viewport, "/enrichment/settings/memory")
    page.get_by_test_id("memory-subject").locator("input").fill(NO_HITS)
    expect(page.get_by_test_id("memory-empty")).to_contain_text("Nothing matches these filters.")
    page.get_by_test_id("memory-clear-filters").click()
    expect(page.get_by_test_id("memory-subject").locator("input")).to_have_value("")

    _goto(page, viewport, "/enrichment/settings/templates/no-such-template-e2e")
    expect(page.get_by_test_id("template-missing")).to_contain_text("This template no longer exists")
    expect(page.get_by_test_id("template-delete")).to_have_count(0)
    page.get_by_test_id("template-missing-back").click()
    expect(page).to_have_url(re.compile(r"/enrichment/settings/templates$"))
    expect(page.get_by_role("heading", level=1)).to_have_text("Settings")

    _goto(page, viewport, f"/enrichment/edit/{GONE_ID}")
    expect(page.get_by_test_id("editor-missing")).to_be_visible()
    page.get_by_test_id("editor-missing-back").click()
    expect(page.get_by_role("heading", level=1)).to_have_text("Enrichment Review")

    _goto(page, viewport, "/enrichment/studio/0000000000000000")
    expect(page.get_by_test_id("run-missing").get_by_role("link")).to_be_visible()

    _goto(page, viewport, f"/pim/products/{EMPTY_SKU}?ai=1")
    drawer = page.get_by_test_id("ai-results-drawer")
    expect(drawer.get_by_test_id("ai-results-empty")).to_contain_text("Pick a template")
    expect(drawer.get_by_test_id("ai-run-custom")).to_be_visible()
    expect(drawer.get_by_test_id("ai-results-review")).to_be_visible()
    _assert_layout(page, phone)


def test_phone_tab_bar_reaches_review_studio_and_settings_and_crumbs_name_their_parent(admin_page: Page):
    page = admin_page
    page.set_viewport_size(VIEWPORTS["phone"])
    _open_panel(page, phone=True)
    tabs = _tab_bar(page).get_by_role("link")
    expect(tabs).to_have_text(["Enrichment Review", "Studio", _entry_name("Settings")])

    page.goto(f"{CMS_BASE_URL}/enrichment/settings/templates/no-such-template-e2e")
    crumbs = page.get_by_role("navigation", name=re.compile("readcrumb", re.I))
    expect(crumbs.get_by_role("link", name="AI templates")).to_be_visible()
    expect(_tab_bar(page).locator("[aria-current='page']")).to_have_text(_entry_name("Settings"))


def test_desktop_sidebar_shows_the_current_entry_after_a_deep_link(admin_page: Page):
    page = admin_page
    page.set_viewport_size({"width": 1280, "height": 600})
    page.goto(f"{CMS_BASE_URL}/enrichment/settings/memory")
    expect(_lit_entry(page, phone=False)).to_have_text(_entry_name("Settings"))
    expect(_lit_entry(page, phone=False)).to_be_in_viewport()
