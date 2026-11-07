@leads @communicator @outbound-glue
Feature: Outbound glue — leads and communicator working together
  As a sales operator
  I want a bad address to be stopped at the moment of sending and an unsubscribe click to stop the person everywhere
  So that outreach stays deliverable and compliant

  Roadmap wave 2 glue (entirius-infra/outbound/work/glue-leads-communicator.md). Needs the leads branch with
  migration 0013, the communicator branch with migrations 0015 and 0016 mounted, and in the stack settings
  `COMMUNICATOR_PRESEND_CHECK = "django_leads.services.verification_service.presend_check"` (see the glue branch of
  zeno `docker/settings_local.py`). The steps reuse the Q3 steps (sender routes, send task, sandbox mail) and Q5 steps
  (company import, verification) — run with both BDD branches merged: `make bdd TAGS=@outbound-glue`. The one-click
  scenario also needs `COMMUNICATOR_UNSUBSCRIBE_BASE_URL` and skips itself without it. A hard bounce cannot be
  produced through the API; that path is covered by the integration test `tests/test_glue_communicator.py` in leads.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "dry_run" mode
    And the beat has drained every due message
    And the sandbox mailbox is empty

  @outbound-glue
  Scenario: Glue an address found invalid is not sent to and the message says why
    Given a fresh company is imported as "company_id"
    And the contact of the company "company_id" gets the address "buyer@mailinator.com"
    When the address of the contact of the company "company_id" is verified
    Then the verification status is "invalid" with the reason "disposable"
    Given the sender route "bdd-glue-a" exists from "bdd-glue-a@ecom.example.test" with copy to "bdd-glue-a@entirius.example.test"
    And the communicator channel is in "sandbox" mode
    When I create a routed approved message to the contact of the company "company_id" on the sender route "bdd-glue-a" as "saved.glue-a"
    And the beat send task has run
    Then the outbound message "saved.glue-a" has status "failed"
    And the outbound message "saved.glue-a" has failure code "presend_check" mentioning "email_invalid"
    And the sandbox mailbox holds no message to the contact of the company "company_id"

  @outbound-glue
  Scenario: Glue the unsubscribe link puts the contact on the shared do-not-contact list
    Given a fresh company is imported as "company_id"
    And the sender route "bdd-glue-b" exists from "bdd-glue-b@ecom.example.test" with copy to "bdd-glue-b@entirius.example.test"
    And the communicator channel is in "sandbox" mode
    When I create a routed approved message to the first contact of the company "company_id" on the sender route "bdd-glue-b" as "saved.glue-b"
    And the beat send task has run
    And the unsubscribe link of the sandbox message to the first contact of the company "company_id" is posted as a one-click request
    Then the last response status is 200
    And the send check of the first contact of the company "company_id" refuses with "opted_out"
