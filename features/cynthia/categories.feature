@cynthia @import-verification
Feature: Cynthia Public Category API
  As an API consumer
  I want to retrieve categories from the public Cynthia API
  So that I can display the category tree in the storefront

  Background:
    Given the test package has been imported

  Scenario: List categories for primary channel
    Given the channel is the primary channel
    When I GET the Cynthia endpoint "categories/"
    Then the response status should be 200
    And the response should be a non-empty list

  Scenario: Categories have required fields
    Given the channel is the primary channel
    When I GET the Cynthia endpoint "categories/"
    Then the response status should be 200
    And each item should have the fields
      | field       |
      | idx         |
      | name        |
      | url_key     |

  Scenario: All imported leaf categories are present
    Given the channel is the primary channel
    And the CSV categories are loaded for the primary channel
    When I GET the Cynthia endpoint "categories/"
    Then the response status should be 200
    And every CSV leaf category should exist in the API response

  Scenario: Categories have product counts
    Given the channel is the primary channel
    When I GET the Cynthia endpoint "categories/"
    Then the response status should be 200
    And each item should have the field "products_count"
