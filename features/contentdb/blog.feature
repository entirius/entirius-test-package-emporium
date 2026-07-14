@contentdb @import-verification
Feature: ContentDB Blog Posts
  As an API consumer
  I want to retrieve blog posts from ContentDB
  So that the storefront can render blog content

  Background:
    Given the test package has been imported

  Scenario: Blog posts exist
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And the response should contain at least 2 items

  Scenario: Blog post by route slug
    When I GET the ContentDB published endpoint "blog-post/" with routes "welcome-to-entirius"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Blog posts have extension field
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And each item should have the field "extension"

  Scenario: Blog posts have extension with images_set
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And at least one item should have extension images_set
