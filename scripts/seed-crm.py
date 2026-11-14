# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CRM configuration of the leads channel (seed.sh Step 4c, after the access staff users and the package import).

Run via:
    docker exec -i <service> python manage.py shell < scripts/seed-crm.py

Rows that point at staff users or at config the YAML fixtures cannot express:
- two communicator mailboxes, one per salesperson (`manager` = the channel default, `editor`), each with its own
  GreenMail login; SMTPS greenmail:3465 (zeno's sandbox backend skips the self-signed certificate), IMAP 3143;
- the event -> stage map: first mail sent -> contacted, a reply -> replied, an out-of-office reply keeps the stage;
- custom fields: a `select` on companies, a `text` on contacts, a `number` on deals; a scoring profile;
- the sales pipeline (three open stages, won, lost) and the channel's default currency;
- owners on a few seeded companies;
- first and last names of the role staff users (fictional), so owners and salespeople show as people; `admin` stays.

The follow-up sequence is not the channel's autostart sequence here: every first mail of the other features would get
follow-ups. The `@crm` scenarios switch `autostart` on and off again themselves. The seeded owners are all `manager`,
whose mailbox is the channel default, so the mail of the older features keeps its sender and its inbox. Reply class
plans stay at their defaults and no reply class profile is created: BDD gives replies their class through the
development endpoint `test/ingest-reply/`. Idempotent (update_or_create); refuses outside development.
"""

import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from django_communicator.models import Channel as CommunicatorChannel
from django_communicator.models import Mailbox
from django_leads.models import AttributeDefinition, Company, DealStage, ScoringProfile, Stage, StageEventRule
from django_leads.models import Channel as LeadsChannel
from django_regional.models import Currency

CHANNEL_IDX = "default-europe"
GREENMAIL = {"smtp_host": "greenmail", "smtp_port": 3465, "smtp_security": "ssl", "imap_host": "greenmail"}
# username -> (address, GreenMail login, default); the login doubles as the password (GreenMail runs without auth).
MAILBOXES = {
    "manager": ("sales1@greenmail.test", "sandbox", True),
    "editor": ("sales2@greenmail.test", "sales2", False),
}
STAGE_EVENTS = {"first_sent": "contacted", "reply": "replied", "reply:out_of_office": None}
ATTRIBUTES = [
    {
        "entity": "company",
        "key": "segment_size",
        "label": "Company size",
        "kind": "select",
        "options": [{"value": v, "label": v.title()} for v in ("small", "medium", "large")],
        "show_in_list": True,
    },
    {"entity": "contact", "key": "linkedin", "label": "LinkedIn profile", "kind": "text"},
    {"entity": "deal", "key": "licences", "label": "Licences", "kind": "number"},
]
SCORING = {
    "thresholds": {"S": 10, "M": 20, "L": 30},
    "rules": [
        {"field": "attr.segment_size", "op": "eq", "value": "large", "points": 20, "label": "large company"},
        {"field": "industry", "op": "contains", "value": "retail", "points": 10, "label": "retailer"},
    ],
    "disqualifiers": [{"field": "industry", "op": "contains", "value": "competitor", "label": "a competitor"}],
}
DEAL_STAGES = [
    ("qualified", "Qualified", "open"),
    ("proposal", "Proposal", "open"),
    ("negotiation", "Negotiation", "open"),
    ("won", "Won", "won"),
    ("lost", "Lost", "lost"),
]
STAFF_NAMES = {
    "manager": ("Anna", "Kowalska"),
    "editor": ("Piotr", "Lis"),
    "viewer": ("Ewa", "Zielinska"),
    "accessadmin": ("Marek", "Lewandowski"),
    "norole": ("Ola", "Wojcik"),
}
OWNERS = {"example-shop-2.test": "manager", "example-shop-3.test": "manager", "example-shop-4.test": "manager"}


def seed_mailboxes(channel: CommunicatorChannel, users: dict) -> None:
    """The two salespeople's mailboxes; any other mailbox of the channel loses the default flag."""
    addresses = [address for address, _, _ in MAILBOXES.values()]
    Mailbox.objects.filter(channel=channel).exclude(address__in=addresses).update(is_default=False)
    for username, (address, login, default) in MAILBOXES.items():
        fields = {"user": users[username], "display_name": username.title(), "is_default": default}
        fields |= {"smtp_user": login, "smtp_password": login, "send_enabled": True}
        fields |= {"imap_port": 3143, "imap_use_ssl": False, "imap_user": login, "imap_password": login}
        Mailbox.objects.update_or_create(
            channel=channel, address=address, defaults=GREENMAIL | fields | {"receive_enabled": True}
        )


def seed_stage_events(channel: LeadsChannel) -> None:
    for event, stage_key in STAGE_EVENTS.items():
        stage = Stage.objects.get(channel=channel, key=stage_key) if stage_key else None
        StageEventRule.objects.update_or_create(channel=channel, event=event, defaults={"target_stage": stage})


def seed_fields(channel: LeadsChannel) -> None:
    for spec in ATTRIBUTES:
        keys = {"entity": spec["entity"], "key": spec["key"]}
        AttributeDefinition.objects.update_or_create(channel=channel, **keys, defaults=spec)
    ScoringProfile.objects.update_or_create(channel=channel, key="leads.scoring", defaults=SCORING)


def seed_deals(channel: LeadsChannel) -> None:
    for order, (key, label, kind) in enumerate(DEAL_STAGES):
        DealStage.objects.update_or_create(
            channel=channel, key=key, defaults={"label": label, "order": order, "kind": kind}
        )
    channel.default_currency = Currency.objects.get(iso3="PLN")
    channel.save(update_fields=["default_currency"])


def seed_owners(channel: LeadsChannel, users: dict) -> None:
    for domain, username in OWNERS.items():
        Company.objects.filter(channel=channel, domain=domain).update(owner=users[username])


def seed_staff_names() -> None:
    for username, (first_name, last_name) in STAFF_NAMES.items():
        get_user_model().objects.filter(username=username).update(first_name=first_name, last_name=last_name)


def main() -> None:
    if getattr(settings, "ENVIRONMENT", "") != "development":
        sys.exit("seed-crm: refusing outside ENVIRONMENT=development")
    users = {user.username: user for user in get_user_model().objects.filter(username__in=["manager", "editor"])}
    leads = LeadsChannel.objects.get(idx=CHANNEL_IDX)
    communicator = CommunicatorChannel.objects.get(idx=CHANNEL_IDX)
    seed_mailboxes(communicator, users)
    seed_stage_events(leads)
    seed_fields(leads)
    seed_deals(leads)
    seed_owners(leads, users)
    seed_staff_names()
    print("CRM seeded: 2 mailboxes, event map, fields, scoring, deal stages, owners, staff names")


main()
