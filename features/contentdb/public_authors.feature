@contentdb @authors @public
Feature: ContentDB Public Author Endpoints
  As a storefront developer
  I want public endpoints to list and retrieve blog authors
  So that I can build author pages and author profile pages

  Background:
    Given the test package has been imported

  # --- List endpoint ---

  Scenario: Public authors list returns only active authors with posts
    When I GET the ContentDB endpoint "authors/"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Inactive authors are excluded from public list
    When I GET the ContentDB endpoint "authors/"
    Then the response status should be 200
    And the results should not contain an item with "slug" equal to "tomasz-kwiatkowski"

  Scenario: Authors with zero posts are excluded from public list
    When I GET the ContentDB endpoint "authors/"
    Then the response status should be 200
    And every author in results should have published_post_count greater than 0

  Scenario: Public author list includes required fields
    When I GET the ContentDB endpoint "authors/"
    Then the response status should be 200
    And every author in results should have the fields
      | field               |
      | uid                 |
      | name                |
      | slug                |
      | role_t9n            |
      | description_t9n     |
      | photo_uid           |
      | photo_url           |
      | published_post_count|

  Scenario: Public author list includes social profiles and contacts
    When I GET the ContentDB endpoint "authors/"
    Then the response status should be 200
    And every author in results should have the fields
      | field               |
      | contact_email       |
      | social_profiles     |

  # --- Detail endpoint ---

  Scenario: Retrieve author by slug
    When I GET the ContentDB endpoint "authors/anna-kowalska/"
    Then the response status should be 200
    And the response data field "name" should equal "Anna Kowalska"
    And the response data field "slug" should equal "anna-kowalska"

  Scenario: Author detail includes full profile data
    When I GET the ContentDB endpoint "authors/anna-kowalska/"
    Then the response status should be 200
    And the response data field "contact_email" should equal "anna@entirius.com"
    And the response data should have the field "social_profiles"
    And the response data should have the field "description_t9n"
    And the response data should have the field "tag_t9n"

  Scenario: Author detail includes published post count
    When I GET the ContentDB endpoint "authors/anna-kowalska/"
    Then the response status should be 200
    And the response data field "published_post_count" should be greater than 0

  Scenario: Non-existent author slug returns 404
    When I GET the ContentDB endpoint "authors/nonexistent-author/"
    Then the response status should be 404

  Scenario: Inactive author slug returns 404 via public endpoint
    When I GET the ContentDB endpoint "authors/tomasz-kwiatkowski/"
    Then the response status should be 404

  # --- Published posts include description_t9n in author brief ---

  Scenario: Published blog post authors include description_t9n
    When I GET the ContentDB published endpoint "blog-post/"
    Then the response status should be 200
    And authors in results should have the fields
      | field           |
      | uid             |
      | name            |
      | slug            |
      | role_t9n        |
      | description_t9n |
      | photo_uid       |
      | photo_url       |

  # --- Filter posts by author ---

  Scenario: Filter published posts by author returns matching posts
    When I GET the ContentDB published endpoint "blog-post/" with author "anna-kowalska"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Filter published posts by non-existent author returns empty
    When I GET the ContentDB published endpoint "blog-post/" with author "nobody-here"
    Then the response status should be 200
    And the response should contain 0 items
