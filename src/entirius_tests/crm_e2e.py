# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""API setup of the CRM e2e (`e2e/cms/test_salesperson_day.py`): a company of the admin, its first mail sent on the
channel clock of the reference week, an interested reply through the development endpoint (no toolbox), so the
owner's Today list holds the task "Interested: answer and open a deal". Every run makes its own companies."""

from __future__ import annotations

import time

from entirius_tests.ai_studio_e2e import AdminApi, wait_for
from entirius_tests.clock import reference_day, reference_week
from entirius_tests.cms_e2e import ADMIN_USERNAME

CHANNEL = "default-europe"
LEADS = f"api/leads/v2/admin/{CHANNEL}/"
COMMUNICATOR = f"api/communicator/v2/admin/{CHANNEL}/"
TODO = f"api/todo/v2/admin/{CHANNEL}/"
HEADER = "company_name,domain,website,lead_type,industry,first_name,last_name,email,job_title,language,legal_basis"


def freeze_clock(api: AdminApi) -> None:
    """Monday 10:00 of the reference week, inside the send window; that week's counters cleared."""
    api.post(f"{COMMUNICATOR}test/clock/", {"iso_datetime": f"{reference_day('monday').isoformat()}T10:00:00+02:00"})
    api.post(f"{COMMUNICATOR}test/reset-counters/", {"days": [day.isoformat() for day in reference_week()]})


def clear_clock(api: AdminApi) -> None:
    api.call("POST", f"{COMMUNICATOR}test/clock/", json={"iso_datetime": None})


def import_company(api: AdminApi, run: str, owner_id: int) -> dict:
    """One company `bdd-e2e-<run>.test` with one contact, owned by `owner_id`; the company detail."""
    domain = f"bdd-e2e-{run}.test"
    row = f"BDD e2e {run},{domain},,RETAILER,garden,Ewa,Nowak,owner@{domain},Owner,pl,legitimate_interest"
    files = {"file": ("bdd-e2e.csv", f"{HEADER}\n{row}\n".encode(), "text/csv")}
    api.call("POST", f"{LEADS}test/import-now/", files=files)
    company = api.get(f"{LEADS}companies/", search=domain)["results"][0]
    api.call("PATCH", f"{LEADS}companies/{company['id']}/", json={"owner_id": owner_id})
    return api.get(f"{LEADS}companies/{company['id']}/")


def draft(api: AdminApi, company: dict) -> int:
    body = {"template_key": "reply.thanks", "contact_id": company["contacts"][0]["id"]}
    return api.post(f"{LEADS}companies/{company['id']}/communicate/", body)["message_id"]


def send_due(api: AdminApi) -> None:
    """The send beat once; waits while the stack's own beat holds its lock (409)."""
    answer = wait_for(lambda: _send_due_once(api), timeout=60)
    if answer is None or answer.status_code != 200:
        raise AssertionError(f"send-due: {getattr(answer, 'status_code', 'locked')}")


def _send_due_once(api: AdminApi):
    response = api.session.post(f"{api.base_url}/{COMMUNICATOR}test/send-due/", json={}, timeout=60)
    return None if response.status_code == 409 else response


def salesperson_day(api: AdminApi) -> dict:
    """A company of the admin with its first mail sent and an interested reply: ids of the company and the task."""
    users = api.get(f"{LEADS}assignable-users/", search=ADMIN_USERNAME)["results"]
    owner = next(user["id"] for user in users if user["username"] == ADMIN_USERNAME)
    company = import_company(api, str(time.time_ns()), owner)
    message_id = draft(api, company)
    api.post(f"{COMMUNICATOR}review/{message_id}/accept/")
    send_due(api)
    thread = api.get(f"{COMMUNICATOR}threads/", subject_ref=f"leads.Company:{company['id']}")["results"][0]
    reply = {"thread_id": thread["id"], "body": "Sounds good, let us talk.", "intent": "interested", "confidence": 0.95}
    api.post(f"{COMMUNICATOR}test/ingest-reply/", reply)
    task = wait_for(lambda: _open_task(api, company["id"]), timeout=30)
    return {"company": company["id"], "domain": company["domain"], "task": task["id"]}


def _open_task(api: AdminApi, company_id: int) -> dict | None:
    rows = api.get(f"{TODO}tasks/", subject_ref=f"leads.Company:{company_id}", status="open")["results"]
    return rows[0] if rows else None
