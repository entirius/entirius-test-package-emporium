# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The BDD channel clock runs in a fixed reference week — it must stay free of PL public holidays."""

from datetime import timedelta

import holidays

from entirius_tests import clock


def test_reference_week_and_next_monday_have_no_pl_holiday():
    days = [*clock.reference_week(), clock.REFERENCE_MONDAY + timedelta(days=7)]
    pl_holidays = holidays.country_holidays("PL", years=clock.REFERENCE_MONDAY.year)

    assert [day for day in days if day in pl_holidays] == []
    assert [clock.reference_day(name).weekday() for name in clock.WEEKDAYS] == list(range(7))
