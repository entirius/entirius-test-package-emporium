# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The storefront's back-in-stock key (seed.sh Step 6: Stock Alerts Storefront Key).

Run via:
    docker exec -i <service> python manage.py shell < scripts/seed-stock-alerts-key.py

Stores `settings.STOCK_ALERTS_API_KEY` (zeno: a dev-only value its storefront build bakes in) as an access token with
the publishable scope `stock_alerts.subscribe` of the primary channel. Access imports only `AGREEMENTS_API_KEY` from
settings, so this key is stored here, by its hash, the way access stores an imported key. The value is never printed.

Idempotent: a token with that hash is kept. Exits quietly when the setting is unset; refuses (exit 1) unless
`settings.ENVIRONMENT == "development"`: a known key must never reach a shared environment.
"""

import sys

from django.conf import settings
from django_access.models import ApiToken, Application
from django_access.services.tokens import hash_key

APPLICATION = "Storefront (seed)"
SCOPE = "stock_alerts.subscribe"
CHANNEL = "default-europe"

if getattr(settings, "ENVIRONMENT", "") != "development":
    print("seed-stock-alerts-key: refused, ENVIRONMENT is not development")
    sys.exit(1)

value = getattr(settings, "STOCK_ALERTS_API_KEY", "")
if not value:
    print("seed-stock-alerts-key: STOCK_ALERTS_API_KEY unset, no key stored")
elif ApiToken.objects.filter(key_hash=hash_key(value), channel_idx=CHANNEL).exists():
    print("seed-stock-alerts-key: key present")
else:
    application, _ = Application.objects.get_or_create(name=APPLICATION)
    ApiToken.objects.create(
        application=application,
        name="Back-in-stock requests",
        key_hash=hash_key(value),
        prefix=value[:6],
        last_four=value[-4:],
        scopes=[SCOPE],
        channel_idx=CHANNEL,
    )
    print("seed-stock-alerts-key: key stored")
