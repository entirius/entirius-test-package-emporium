@contentdb @import-verification
Feature: ContentDB Routes and Content Types
  As an API consumer
  I want to retrieve routes and content type definitions
  So that the storefront can resolve URL slugs to content

  Background:
    Given the test package has been imported

  Scenario: Routes list is non-empty
    When I GET the ContentDB endpoint "routes/"
    Then the response status should be 200
    And the response should be a non-empty list

  Scenario: Home route exists
    When I GET the ContentDB endpoint "routes/"
    Then the response status should be 200
    And the item with "url" equal to "home" should exist

  Scenario: Content types include expected types
    When I GET the ContentDB endpoint "content-types/"
    Then the response status should be 200
    And the response should contain at least 3 items
