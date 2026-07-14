@matrix @import-verification @options
Feature: Matrix Options (Filterable Attributes)
  Verify that the options endpoint returns filter groups based on
  FilterableFeatures configuration in the Matrix channel.

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  Scenario: Options endpoint returns filter groups
    When I GET the Matrix endpoint "options/"
    Then the response status should be 200
    And the options response should contain at least 4 filter groups

  Scenario: Series filter group has values with counts
    When I GET the Matrix endpoint "options/"
    Then the response status should be 200
    And the options filter group "series" should have values
    And each value in filter group "series" should have a product count

  Scenario: Options filter group has correct structure
    When I GET the Matrix endpoint "options/"
    Then the response status should be 200
    And each filter group should have fields "idx", "label", "filter_type"

  Scenario: Boolean filter (is_handcrafted) appears in options
    When I GET the Matrix endpoint "options/"
    Then the response status should be 200
    And the options response should contain filter group "is_handcrafted"
