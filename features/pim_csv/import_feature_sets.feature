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
