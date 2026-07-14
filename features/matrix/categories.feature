@matrix @matrix-categories @import-verification
Feature: Matrix Categories Listing API
  As an API consumer
  I want to retrieve categories from the Matrix categories endpoint
  So that I can display navigation without depending on Cynthia

  Background:
    Given the test package has been imported

  Scenario: List categories for primary channel
    Given the channel is the primary channel
    When I GET the Matrix endpoint "categories/"
    Then the response status should be 200
    And the response should be a non-empty list

  Scenario: Categories have required fields
    Given the channel is the primary channel
    When I GET the Matrix endpoint "categories/"
    Then the response status should be 200
    And each item should have the fields
      | field           |
      | idx             |
      | name            |
      | url_key         |
      | tree_deep       |
      | position        |
      | has_children    |
      | products_count  |

  Scenario: Depth filter returns only top-level categories
    Given the channel is the primary channel
    When I GET the Matrix endpoint "categories/" with params
      | param | value |
      | depth | 1     |
    Then the response status should be 200
    And the response should be a non-empty list
    And every category should have tree_deep equal to 1

  Scenario: Categories match Cynthia output
    Given the channel is the primary channel
    When I GET the Matrix endpoint "categories/" with params
      | param | value |
      | depth | 1     |
    Then the response status should be 200
    And I save the Matrix categories response
    When I GET the Cynthia endpoint "categories/" with params
      | param | value |
      | depth | 1     |
    Then the response status should be 200
    And the Matrix categories should match Cynthia categories by idx and name

  Scenario: All imported leaf categories are present
    Given the channel is the primary channel
    And the CSV categories are loaded for the primary channel
    When I GET the Matrix endpoint "categories/"
    Then the response status should be 200
    And every CSV leaf category should exist in the API response

  Scenario: Categories have product counts
    Given the channel is the primary channel
    When I GET the Matrix endpoint "categories/"
    Then the response status should be 200
    And each item should have the field "products_count"

  Scenario: Invalid channel returns 404
    Given the channel is "nonexistent-channel-bdd"
    When I GET the Matrix endpoint "categories/"
    Then the response status should be 404

  Scenario: Categories include meta fields
    Given the channel is the primary channel
    When I GET the Matrix endpoint "categories/"
    Then the response status should be 200
    And each item should have the fields
      | field            |
      | meta_title       |
      | meta_description |
      | description      |
      | parent_idx       |
