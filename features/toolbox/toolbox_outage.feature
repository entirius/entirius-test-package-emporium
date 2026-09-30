@toolbox-down @toolbox-oneshot @v2 @admin
Feature: AI toolbox outage — degraded mode and automatic recovery
  As an operator of a stack whose AI toolbox went down
  I want failed drafts and intel analyses to be visible during the outage and retried once it is back
  So that nobody has to click every company after an outage

  The outage is simulated with the communicator development endpoint test/toolbox-outage/ (the
  django_utils.toolbox.outage switch, AI_TOOLBOX_TEST_SWITCH in zeno); after_scenario turns it off even when a
  step fails. The retry beat tasks run through test/retry-drafts/ and test/retry-analyses/. Needs the toolbox up
  (make toolbox-check). One-shot: it consumes a failed draft and the example-shop-6.test analysis — re-run after
  `make seed`.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: an outage fails a draft and an analysis with alerts, recovery retries both
    Given the AI toolbox outage switch is on
    When I request the "lead.cold.shop" message for "jan@example-shop-1.test" about "bdd:toolbox-down"
    Then the response status should be 201
    And the response field "status" should equal "failed"
    And the response field "failure_code" should equal "upstream"
    And I save the response field "id" as "saved.draft"
    And a notification titled "Message draft failed: upstream (lead.cold.shop)" exists
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-6.test"
    Then I save the first result field "id" as "company_id"
    When I POST to the v2 admin endpoint "siteintel/admin/{channel_idx}/audits/" with body
      """
      {"domain_or_url": "example-shop-6.test", "requested_by": "bdd:toolbox-down"}
      """
    Then I save the response field "id" as "audit_id"
    When the audit test run of "audit_id" has completed
    Then the company "company_id" has an activity "intel" containing "analysis failed: ToolboxConnectionError"
    And a notification titled "Intel analysis failed" exists
    When the communicator retries failed drafts
    Then the retry recovered 0 and failed 0
    And the message "saved.draft" has status "failed"
    When the AI toolbox outage switch is turned off
    And the communicator retries failed drafts
    Then the message "saved.draft" has status "review_required"
    When leads retries failed intel analyses
    Then the company "company_id" has an activity "intel" containing "intel analysed"
