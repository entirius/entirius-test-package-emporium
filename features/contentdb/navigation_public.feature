@contentdb @navigation
Feature: Navigation Public API
  As a storefront application
  I want to fetch published navigation content
  So that I can render the site header and footer menus

  Background:
    Given the test package has been imported

  Scenario: Get published navigation for header type returns 200
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200

  Scenario: Published navigation response has required fields
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the response should have the fields
      | field   |
      | uid     |
      | name    |
      | content |

  Scenario: Navigation content field is a dict
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the response field "content" should be a dict

  Scenario: Navigation content has items list
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the navigation content should have items

  Scenario: Navigation has 4 top-level items
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the navigation content should have 4 items

  Scenario: Navigation items include megamenu type
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the navigation items should include display_as "megamenu"

  Scenario: Navigation items include link type
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the navigation items should include display_as "link"

  Scenario: First navigation item is FURNITURE megamenu
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the first navigation item should have label "FURNITURE"
    And the first navigation item should have display_as "megamenu"

  Scenario: FIND A STORE item is a link type
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the navigation item with label "FIND A STORE" should have display_as "link"

  Scenario: Megamenu item has columns
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the first navigation item should have columns

  Scenario: First megamenu has 3 columns
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the first navigation item should have 3 columns

  Scenario: First column heading is Shop by Category
    When I GET the v2 admin endpoint "contentdb/navigation/header/"
    Then the response status should be 200
    And the first column of the first navigation item should have heading "Shop by Category"

  Scenario: Unpublished footer navigation returns 404
    When I GET the v2 admin endpoint "contentdb/navigation/footer/"
    Then the response status should be 404

  Scenario: Non-existent content type returns 404
    When I GET the v2 admin endpoint "contentdb/navigation/nonexistent/"
    Then the response status should be 404

  Scenario: Navigation endpoint accepts language parameter
    When I GET the v2 admin endpoint "contentdb/navigation/header/?language=EN"
    Then the response status should be 200
