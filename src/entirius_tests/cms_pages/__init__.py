"""CMS page objects for the leads funnel e2e. Every user action counts a tap (`self.taps`)."""

from entirius_tests.cms_pages.inbox import InboxPage
from entirius_tests.cms_pages.notifications import NotificationBar
from entirius_tests.cms_pages.thread import ThreadPage

__all__ = ["InboxPage", "NotificationBar", "ThreadPage"]
