@leads @v2 @admin
Feature: Leads — retention and GDPR export and erasure
  As a data controller
  I want personal data of idle contacts to expire and a data subject's data to be exportable and erasable
  So that the platform keeps only what it may keep, and nothing is sent to an erased address

  Data: fixtures/django_leads_retention.cfg.yaml — example-stale.test (contacted, idle since 2025) and
  example-stale-won.test (won, as old) for L-16; example-gdpr.test for L-17, with one sent communicator thread each
  (fixtures/django_communicator.cfg.yaml). Both scenarios are one-shot: they pseudonymise seeded rows — re-run after
  `make seed`. Edge cases: L-16, L-17.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  @leads-oneshot
  Scenario: L-16 contacts of a company idle past retention are anonymised; company, stage and thread follow
    Given the leads contact "stale@example-stale.test" of the company "example-stale.test" is saved as "stale"
    And the leads contact "won@example-stale-won.test" of the company "example-stale-won.test" is saved as "won"
    And the communicator thread to "stale@example-stale.test" about the company "stale.company" is saved as "thread"
    When I run the leads test action "anonymise-now" as of "+1 day"
    Then the contact "stale" is anonymised
    And the company "stale.company" is in stage "contacted"
    And the company "stale.company" has an activity "anonymised" containing "contact anonymised"
    And the communicator thread "thread" has recipient "{stale.email}"
    And the contact "won" is not anonymised

  @leads-oneshot
  Scenario: L-17 GDPR export spans leads, communicator and agreements; after erasure nothing reaches the address
    Given the leads contact "erase@example-gdpr.test" of the company "example-gdpr.test" is saved as "subject"
    When I POST to the v2 admin endpoint "leads/admin/gdpr/export/" with body
      """
      {"email": "erase@example-gdpr.test"}
      """
    Then the response status should be 200
    And the GDPR response lists the modules "django_leads, django_communicator, django_agreements"
    And the GDPR export lists "erase@example-gdpr.test" in "django_leads.Contact, django_communicator.Thread, django_agreements.ConsentRecord, django_agreements.ObjectionEvent, django_agreements.OrderAgreementSnapshot"
    When I POST to the v2 admin endpoint "leads/admin/gdpr/erase/" with body
      """
      {"email": "erase@example-gdpr.test"}
      """
    Then the response status should be 200
    And the GDPR erasure touched rows in "django_leads, django_communicator, django_agreements"
    And the contact "subject" is anonymised
    When I POST to the v2 admin endpoint "leads/admin/gdpr/export/" with body
      """
      {"email": "erase@example-gdpr.test"}
      """
    Then the response status should be 200
    And the GDPR export lists "{subject.email}" in "django_agreements.ConsentRecord, django_agreements.ObjectionEvent, django_agreements.OrderAgreementSnapshot"
    And the GDPR export holds no "erase@example-gdpr.test"
    And the communicator suppressions list the global token "{subject.email}"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/companies/{subject.company}/communicate/" with body
      """
      {"template_key": "lead.cold.b2b", "contact_id": {subject}}
      """
    Then the response status should be 409
    Given the sandbox mailbox count is remembered
    When I request the "lead.cold.b2b" message for "erase@example-gdpr.test" about "leads.Company:152"
    Then the nested response field "status" should equal "suppressed"
    When the communicator beat sends due messages
    Then the sandbox mailbox count is unchanged
    When I import the leads contact "erase@example-gdpr.test" of the company "example-gdpr.test"
    Then the import report should contain the reason "erased_address"
    And the company "subject.company" has no contact "erase@example-gdpr.test"
