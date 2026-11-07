@leads @outbound-b-edge
Feature: Outbound reporting edge cases — refusals and empty results of scoring, pilots and the funnel report
  As a sales operator
  I want clear refusals and empty answers where there is nothing to score, no valid pilot or no data
  So that the CMS screens never show a broken state

  Roadmap T3 (entirius-infra/outbound/roadmap.md), the unhappy paths of B3, B9 and B5. Companion of
  `outbound_t3.feature` (happy paths, tag @outbound-b); this file is tagged @outbound-b-edge. Every scenario makes its
  own company; the scoring profile is removed when its scenario ends. Needs the leads build with migrations 0009-0011.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  @t3-s6
  Scenario: B3 scoring a company with no profile is refused
    Given the channel has no scoring profile
    And a fresh company is imported as "company_id"
    When the company "company_id" is scored expecting status 409
    Then the error code is "NO_SCORING_PROFILE"

  @t3-s6
  Scenario: B3 a disqualifier forces S4 whatever the points
    Given an active scoring profile with a disqualifier on the domain text "bdd-"
    And a fresh company is imported as "company_id"
    When the company "company_id" is scored expecting status 200
    Then the score is disqualified and segment "S4"

  @t3-s7
  Scenario: B9 a pilot that ends before it starts is refused
    Given a fresh company is imported as "company_id"
    When a pilot for the company "company_id" ends before it starts
    Then the response status should be 400

  @t3-s7
  Scenario: B9 a pilot for a company that does not exist is a 404
    When a pilot is started for the company id 999999999
    Then the response status should be 404

  @t3-s7
  Scenario: B9 the pilot report always carries every result key
    When the pilot report is read
    Then the pilot report has every result key and a numeric total

  @t3-s8
  Scenario: B5 a funnel window that ends before it starts is refused
    When the funnel report is read with a window that ends before it starts
    Then the response status should be 400

  @t3-s8
  Scenario: B5 an origin nobody uses gives an empty funnel
    When the funnel report is read for the origin "bdd-no-such-origin"
    Then the funnel report has no companies and no transitions

  @t3-s8
  Scenario: B5 moving a company to an unknown stage is a 404
    Given a fresh company is imported as "company_id"
    When the company "company_id" is moved to the unknown stage "bdd-no-such-stage"
    Then the response status should be 404

  @t3-s8
  Scenario: B5 the company list filters by origin
    Given a fresh company with origin "bdd-list" is imported as "company_id"
    Then the companies list filtered by the origin of "company_id" returns exactly "company_id"
