@spec-first @contact-forms @leads @admin @v2
Feature: Contact Forms — Admin Lead API (v2.1.0)
  As an operator using the CMS
  I want to list, filter, transition, and summarise leads
  So that I can manage the sales pipeline

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: List leads requires authentication
    When I GET the v2 admin endpoint "contact-forms/admin/leads/" without auth
    Then the response status should be 401

  Scenario: List leads returns paginated results
    When I GET the v2 admin endpoint "contact-forms/admin/leads/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Filter leads by status
    When I GET the v2 admin endpoint "contact-forms/admin/leads/?status=new"
    Then the response status should be 200
    And every result should have "status" equal to "new"

  Scenario: Lead summary aggregates by status
    When I GET the v2 admin endpoint "contact-forms/admin/leads/summary/"
    Then the response status should be 200
    And the response should contain key "by_status"

  Scenario: Disallowed status transition returns 400
    Given a lead exists in status "new"
    When I POST the v2 admin endpoint "contact-forms/admin/leads/{lead_id}/transition/" with body
      """
      {"new_status": "won"}
      """
    Then the response status should be 400
    And the response detail should contain "Cannot transition"

  Scenario: Allowed status transition succeeds
    Given a lead exists in status "new"
    When I POST the v2 admin endpoint "contact-forms/admin/leads/{lead_id}/transition/" with body
      """
      {"new_status": "contacted"}
      """
    Then the response status should be 200
    And the response should have "status" equal to "contacted"
