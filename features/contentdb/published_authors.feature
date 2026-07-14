@contentdb @authors @import-verification
Feature: Published Blog Post Authors
  As a storefront developer
  I want published blog posts to include author data
  So that I can display author profiles on posts

  Background:
    Given the test package has been imported

  Scenario: Published blog posts include authors field
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And each item should have the field "authors"

  Scenario: Published blog posts include co_authors field
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And each item should have the field "co_authors"

  Scenario: At least one published blog post has authors assigned
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And at least one result should have non-empty "authors" array

  Scenario: At least one published blog post has co-authors assigned
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And at least one result should have non-empty "co_authors" array

  Scenario: At least one published blog post has no authors (backwards compat)
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And at least one result should have empty "authors" array

  Scenario: Author object has required fields
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And authors in results should have the fields
      | field |
      | uid   |
      | name  |
      | slug  |

  Scenario: Filter published blog posts by author slug
    When I GET the ContentDB published endpoint "blog-post/" with author "anna-kowalska"
    Then the response status should be 200
    And the response should contain at least 1 items
