@leads @v2 @admin
Feature: Leads — stage rules, intel analysis, recipient pick and rotation
  As a sales operator
  I want entering a stage or finishing an audit to leave a reviewable draft for the right person
  So that nobody is written to without email, legal basis, hooks or after asking not to be contacted

  Rules of fixtures/django_leads.cfg.yaml: new → request_audit, intel_ready → lead.cold.shop (ai_pick, hooks
  required), contacted → lead.cold.b2b (primary). Stage changes are evaluated by the worker, `test/evaluate/`
  runs the same rules synchronously; timeline checks poll. The fake toolbox answers `leads.analysis` with three
  hooks and `leads.pick_recipient` with the first candidate that has an email. Edge cases: L-08…L-12, L-14.
  L-14 is one-shot (it walks three example-shop-4 sequences and parks the company) — re-run after `make seed`.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: L-08 a company without any contact email is skipped, never drafted, and a skip starts no cooldown
    Given the leads company "no-email-shop.test" exists as "company_id"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/companies/{company_id}/transition/" with body
      """
      {"stage_key": "contacted"}
      """
    And I run the leads test action "evaluate" with body
      """
      {"company_id": {company_id}, "trigger": "stage_entered", "stage_key": "contacted"}
      """
    And I run the leads test action "evaluate" with body
      """
      {"company_id": {company_id}, "trigger": "stage_entered", "stage_key": "contacted"}
      """
    Then the response status should be 200
    And the company "company_id" has an activity "skipped" containing "skipped: no email"
    And the company "company_id" has a rule run "skipped"
    And the review queue holds no draft about the company "company_id"

  Scenario: L-09 a do_not_contact company is blocked before communicator
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-7.test"
    Then I save the first result field "id" as "company_id"
    When I run the leads test action "evaluate" with body
      """
      {"company_id": {company_id}, "trigger": "stage_entered", "stage_key": "contacted"}
      """
    Then the response status should be 200
    And the company "company_id" has an activity "blocked" containing "blocked: do_not_contact"
    And the review queue holds no draft about the company "company_id"

  Scenario: L-10 entering the same stage twice within the cooldown fires the rule once
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-3.test"
    Then I save the first result field "id" as "company_id"
    When the company "company_id" moves through the stages "contacted, new, contacted"
    Then the company "company_id" has an activity "rule" containing "rule cooldown"
    And the company "company_id" has a rule run "fired"

  Scenario: L-11 intel ready with zero hooks skips a rule that requires hooks
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-6.test"
    Then I save the first result field "id" as "company_id"
    When I run the leads test action "evaluate" with body
      """
      {"company_id": {company_id}, "trigger": "intel_ready"}
      """
    Then the response status should be 200
    And the company "company_id" has an activity "skipped" containing "skipped: no hooks"

  Scenario: L-12 a finished audit gives hooks and a draft for the AI-picked contact
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-4.test"
    Then I save the first result field "id" as "company_id"
    When I POST to the v2 admin endpoint "siteintel/admin/{channel_idx}/audits/" with body
      """
      {"domain_or_url": "example-shop-4.test", "requested_by": "bdd:l-12"}
      """
    Then I save the response field "id" as "audit_id"
    When the audit test run of "audit_id" has completed
    Then the company "company_id" has a rule run "fired"
    And the company "company_id" has an activity "intel" containing "intel analysed"
    And the company "company_id" has an activity "rule" containing "recipient picked"
    And the company "company_id" has an activity "draft" containing "draft review_required"
    And the review queue holds a draft about the company "company_id"

  @leads-oneshot
  Scenario: L-14 silence after the sequence rotates to the next contact, then parks the company
    The extra contact guarantees a second rotation whether or not leads_import added its form contact first.
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-4.test"
    Then I save the first result field "id" as "company_id"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/contacts/" with body
      """
      {"company_id": {company_id}, "email": "bdd-zofia@example.com", "first_name": "Zofia", "legal_basis": "legitimate_interest"}
      """
    Then the response status should be 201
    When the follow-up sequence to "piotr@example-shop-4.test" about the company "company_id" has finished
    And I run the leads test action "rotate-now" with body
      """
      {}
      """
    Then the company "company_id" has an activity "rotation" containing "rotated to the next contact"
    And the company "company_id" has rotation count 1
    When the latest follow-up sequence about the company "company_id" has finished
    And I run the leads test action "rotate-now" with body
      """
      {}
      """
    Then the company "company_id" has rotation count 2
    When the latest follow-up sequence about the company "company_id" has finished
    And I run the leads test action "rotate-now" with body
      """
      {}
      """
    Then the company "company_id" is in stage "unresponsive"
