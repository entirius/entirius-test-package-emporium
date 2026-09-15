@pim-csv @import-verification @feature-sets
Feature: PIM Feature Set Verification
  Verify that all configured feature sets from CSV are loaded correctly.

  Background:
    Given the test package has been imported

  Scenario: All configured feature sets exist
    Given the CSV feature sets are loaded
    Then the feature sets should include "default", "furniture", "bundle", "custom", "premium"

  Scenario: Feature set count matches CSV
    Given the CSV feature sets are loaded
    Then the feature set count should match CSV

  Scenario: Features of every set match the CSV
    Given I am authenticated as an admin user
    And the CSV feature sets are loaded
    Then the features of every CSV feature set should match the API

  Scenario: Feature positions in every set match the CSV
    Given I am authenticated as an admin user
    And the CSV feature positions are loaded
    Then the feature positions of every CSV feature set should match the API

  Scenario Outline: Bundle limit features keep system scope
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pim/admin/features/<idx>/"
    Then the response status should be 200
    And the response field "scope_name" should equal "system"

    Examples:
      | idx              |
      | max_limit_bundle |
      | min_limit_bundle |
