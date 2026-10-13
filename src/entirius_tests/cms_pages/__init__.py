"""CMS page objects for the leads funnel e2e. Every user action counts a tap (`self.taps`)."""

from entirius_tests.cms_pages.board import BoardPage
from entirius_tests.cms_pages.company import CompanyPage
from entirius_tests.cms_pages.import_dialog import LeadsImportPage
from entirius_tests.cms_pages.inbox import InboxPage
from entirius_tests.cms_pages.notifications import NotificationBar
from entirius_tests.cms_pages.settings import SettingsPage
from entirius_tests.cms_pages.stages import StagesPage
from entirius_tests.cms_pages.thread import ThreadPage

__all__ = [
    "BoardPage",
    "CompanyPage",
    "InboxPage",
    "LeadsImportPage",
    "NotificationBar",
    "SettingsPage",
    "StagesPage",
    "ThreadPage",
]
