@contentdb @import-verification
Feature: ContentDB Image Gallery
  As an API consumer
  I want to verify the image gallery is populated
  So that CMS pages can reference uploaded images

  Background:
    Given the test package has been imported

  Scenario: Image gallery is populated
    When I GET the ContentDB endpoint "images/"
    Then the response status should be 200
    And the response should contain at least 4 items

  Scenario: Images have required fields
    When I GET the ContentDB endpoint "images/"
    Then the response status should be 200
    And each item should have the fields
      | field  |
      | uid    |
      | image  |
      | width  |
      | height |
