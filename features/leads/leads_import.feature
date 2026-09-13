@leads @v2 @admin
Feature: Leads — CSV import and contact form bridge
  As a sales operator
  I want companies and contacts to enter the pipeline from a CSV file and from contact forms
  So that the same company never exists twice and every contact carries its legal basis

  Not one-shot: the import is idempotent (a re-run matches instead of creating) and form submissions
  upsert. Data: fixtures/django_leads.cfg.yaml, the leadcreationrule of django_contact_forms.cfg.yaml,
  package/leads--default-europe.csv (12 rows: 9 imported, 3 skipped). Edge cases: L-01, L-04, L-06, L-07, L-19.
  contact_forms rejects reserved `.test` addresses, so submissions name the company by the `website` body key.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: L-01 two spellings of one registrable domain become one company
    When I upload the package file "leads--default-europe.csv" to the v2 admin endpoint "leads/admin/{channel_idx}/imports/"
    Then the response status should be 202
    And I save the response field "id" as "batch_id"
    And the import batch "batch_id" has finished
    And the response field "skipped_count" should equal integer 3
    And the import report row 3 should have action "matched"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=lesna-shop.pl"
    Then the response status should be 200
    And the response field "count" should equal integer 1

  Scenario: L-04 a row without domain and email is skipped with a reason
    When I upload the package file "leads--default-europe.csv" to the v2 admin endpoint "leads/admin/{channel_idx}/imports/"
    Then the response status should be 202
    And I save the response field "id" as "batch_id"
    And the import batch "batch_id" has finished
    And the import report should contain the reason "no_domain_no_email"
    And the import report should contain the reason "freemail_no_domain"
    And the import report should contain the reason "invalid_legal_basis"

  Scenario: L-06 a form submission adds a contact to the existing company
    When I submit a contact form on channel "default-europe" with body
      """
      {"email": "form.buyer@example.com", "body": {"name": "Form Buyer", "website": "https://www.example-shop-4.test/", "marketing_consent": true}}
      """
    And I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-4.test"
    Then the response field "count" should equal integer 1
    And I save the first result field "id" as "company_id"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/contacts/?company={company_id}"
    Then the results should contain an item with "email" equal to "form.buyer@example.com"
    And the results should contain an item with "legal_basis" equal to "consent"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/activities/?company={company_id}"
    Then the results should contain an item with "kind" equal to "form"

  Scenario: L-07 a form submission without marketing consent leaves the legal basis empty
    When I submit a contact form on channel "default-europe" with body
      """
      {"email": "no.consent@example.com", "body": {"name": "No Consent", "website": "https://www.example-shop-5.test/"}}
      """
    And I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-5.test"
    Then I save the first result field "id" as "company_id"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/contacts/?company={company_id}"
    Then the result with "email" equal to "no.consent@example.com" should have a null "legal_basis"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/activities/?company={company_id}"
    Then the results should contain an item with "message" equal to "no legal basis"

  Scenario: L-19 a submission on a channel without a lead creation rule reaches nothing in leads
    When I submit a contact form on channel "default-local" with body
      """
      {"email": "local.visitor@example.com", "body": {"name": "Local Visitor", "website": "https://www.example-shop-6.test/", "marketing_consent": true}}
      """
    And I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-6.test"
    Then I save the first result field "id" as "company_id"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/contacts/?company={company_id}"
    Then the results should not contain an item with "email" equal to "local.visitor@example.com"
