@leads @outbound-b
Feature: Outbound reporting — scoring, pilots and the funnel report by origin
  As a sales operator
  I want to rank companies, track pilots and see where each origin loses leads
  So that the outbound plan can be judged on numbers

  Roadmap T3 (entirius-infra/outbound/roadmap.md): B3 scoring S1-S4, B9 pilot stage, B5 funnel report with the
  company origin. These scenarios need the leads build that carries them (migrations 0009-0011); on the stack
  without it run only `make bdd TAGS=@outbound` (this feature is tagged @outbound-b). Every scenario makes its own company, so none
  consumes the seed; the scoring profile is removed when its scenario ends.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  @t3-s6
  Scenario: B3 a retailer scores 30 points and lands in S1
    Given an active scoring profile that gives retailers 30 points
    And a fresh company is imported as "company_id"
    When the company "company_id" is scored
    Then the score is segment "S1" with 30 points
    And the company "company_id" has an activity "score" containing "S1"

  @t3-s7
  Scenario: B9 a pilot with a success criterion ends as a success and shows in the report
    Given a fresh company is imported as "company_id"
    When a pilot of 30 days is started for the company "company_id"
    And the pilot of the company "company_id" is marked "success"
    Then the pilot report counts at least 1 successful pilot
    And the company "company_id" has an activity "note" containing "pending -> success"

  @t3-s8
  Scenario: B5 the funnel report counts a stage transition for one origin
    Given a fresh company with origin "bdd-partner" is imported as "company_id"
    When the company "company_id" moves to the stage "contacted"
    Then the funnel report of the origin of "company_id" shows 1 company and a transition "new" to "contacted"
