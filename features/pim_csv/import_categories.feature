@pim-csv @import-verification
Feature: Category Import Verification
  As a platform operator
  I want to verify that CSV-imported categories match the API
  So that I know the import pipeline works correctly

  Background:
    Given the test package has been imported

  Scenario: All CSV leaf categories exist in primary channel API
    Given the channel is the primary channel
    And the CSV categories are loaded for the primary channel
    When I GET the Matrix endpoint "categories/"
    Then the response status should be 200
    And every CSV leaf category should exist in the API response

  Scenario: API has at least as many categories as CSV leaf categories
    Given the channel is the primary channel
    And the CSV categories are loaded for the primary channel
    When I GET the Matrix endpoint "categories/"
    Then the response status should be 200
    And the API category count should be at least the CSV leaf count
