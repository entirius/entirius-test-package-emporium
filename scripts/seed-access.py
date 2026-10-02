# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Access staff users (seed.sh Step 3e, after the test users).

Run via:
    docker exec -i <service> python manage.py shell < scripts/seed-access.py

Creates or resets one staff user (not superuser) per built-in role plus `norole` (staff without a role), each with
an EN `Customer` row and a verified primary `EmailAddress` so the CMS login works. Passwords are the dev defaults
`<username>123` (README § Key settings) — never printed. Roles are granted through
`django_access.services.access_service.grant_role` with the system actor, so every grant carries its audit row.

Idempotent: an existing user gets its password and flags reset; an existing grant is kept.
Refuses (exit 1) unless `settings.ENVIRONMENT == "development"`: weak passwords on staff accounts must never reach a
shared environment. Exits quietly when `django_access` is not installed.
"""

import sys

from allauth.account.models import EmailAddress
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django_accounts.models import Customer
from django_regional.models import Language

# username -> built-in role key (None = staff without a role)
ACCESS_USERS = {
    "viewer": "viewer",
    "editor": "editor",
    "manager": "manager",
    "accessadmin": "administrator",
    "norole": None,
}


def upsert_staff_user(username: str):
    user, created = get_user_model().objects.get_or_create(
        username=username, defaults={"email": f"{username}@entirius.com"}
    )
    user.set_password(f"{username}123")
    user.is_active, user.is_staff, user.is_superuser = True, True, False
    user.save()
    lang = Language.objects.get(iso2__iexact="EN")
    defaults = {"is_active": True, "is_verified": True, "language": lang}
    Customer.objects.update_or_create(user=user, defaults=defaults)
    EmailAddress.objects.get_or_create(user=user, email=user.email, defaults={"verified": True, "primary": True})
    return user, created


def ensure_grant(user, role_key: str) -> bool:
    from django_access.models import Grant, Role
    from django_access.services.access_service import Actor, grant_role

    role = Role.objects.get(key=role_key)
    if Grant.objects.filter(role=role, user=user).exists():
        return False
    grant_role(role, user=user, actor=Actor())
    return True


def main() -> None:
    if not apps.is_installed("django_access"):
        print("access not installed — skipping access staff users")
        return
    if getattr(settings, "ENVIRONMENT", None) != "development":
        sys.exit("seed-access: refused — ENVIRONMENT is not 'development' (dev passwords on staff accounts)")
    for username, role_key in ACCESS_USERS.items():
        user, created = upsert_staff_user(username)
        granted = ensure_grant(user, role_key) if role_key else False
        state = "created" if created else "reset"
        print(f"{username}: {state}, role={role_key or '-'}{' (granted)' if granted else ''}")


main()
