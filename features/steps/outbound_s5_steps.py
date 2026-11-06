# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Steps for the S5 settings scenarios (`@s5-settings`)."""

from __future__ import annotations

from behave import then


@then('the response should not contain the field "{field}"')
def step_response_lacks_field(context, field):
    data = context.response_data
    assert field not in data, f"Field '{field}' must not be returned. Keys: {list(data.keys())}"
