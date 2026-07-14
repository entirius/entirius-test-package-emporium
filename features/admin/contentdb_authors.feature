@contentdb @authors @admin @v2
Feature: ContentDB Author Admin API
  As a CMS admin
  I want to manage blog authors
  So that I can assign authors to blog posts

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- Authentication ---

  Scenario: Unauthenticated request returns 401
    When I GET the v2 admin endpoint "contentdb/admin/authors/" without auth
    Then the response status should be 401

  Scenario: Non-admin user returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "contentdb/admin/authors/"
    Then the response status should be 403

  Scenario: Unauthenticated request returns structured error
    When I GET the v2 admin endpoint "contentdb/admin/authors/" without auth
    Then the response status should be 401
    And the error response should have error code "AUTHENTICATION_REQUIRED"
    And the error response should have a debug_id

  Scenario: Non-admin request returns structured error
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "contentdb/admin/authors/"
    Then the response status should be 403
    And the error response should have error code "PERMISSION_DENIED"
    And the error response should have a debug_id

  # --- List ---

  Scenario: List authors returns paginated structure
    When I GET the v2 admin endpoint "contentdb/admin/authors/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: List authors returns fixture authors
    When I GET the v2 admin endpoint "contentdb/admin/authors/"
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "slug" equal to "anna-kowalska"
    And the results should contain an item with "slug" equal to "jan-nowak"

  Scenario: List authors respects page_size parameter
    When I GET the v2 admin endpoint "contentdb/admin/authors/" with params
      | param     | value |
      | page_size | 2     |
    Then the response status should be 200
    And the results should contain at most 2 items

  Scenario: List authors with search filter
    When I GET the v2 admin endpoint "contentdb/admin/authors/" with params
      | param  | value |
      | search | Anna  |
    Then the response status should be 200
    And the results should contain an item with "slug" equal to "anna-kowalska"
    And the results should not contain an item with "slug" equal to "jan-nowak"

  # --- Create ---

  Scenario: Create author with full data
    Given I ensure contentdb author with slug "bdd-full-author" is cleaned up
    When I POST to the v2 admin endpoint "contentdb/admin/authors/" with body
      """
      {
        "name": "BDD Full Author",
        "slug": "bdd-full-author",
        "role_t9n": {"en": "Tester", "pl": "Tester"},
        "description_t9n": {"en": "A BDD test author"},
        "tag_t9n": {"en": "bdd"},
        "contact_email": "bdd@test.com",
        "contact_phone": "+48 000 000 000",
        "contact_url": "https://bdd.test",
        "social_profiles": {"twitter": "https://x.com/bdd"},
        "is_active": true
      }
      """
    Then the response status should be 201
    And the response field "name" should equal "BDD Full Author"
    And the response field "slug" should equal "bdd-full-author"
    And the response field "is_active" should be true
    And the response field "contact_email" should equal "bdd@test.com"

  Scenario: Create author with minimal data generates slug automatically
    Given I ensure contentdb author with slug "minimal-author" is cleaned up
    When I POST to the v2 admin endpoint "contentdb/admin/authors/" with body
      """
      {"name": "Minimal Author"}
      """
    Then the response status should be 201
    And the response field "slug" should equal "minimal-author"

  Scenario: Create author requires name
    When I POST to the v2 admin endpoint "contentdb/admin/authors/" with body
      """
      {"slug": "no-name-author"}
      """
    Then the response status should be 400

  # --- Retrieve ---

  Scenario: Retrieve author by uid
    Given I create a test contentdb author "BDD Retrieve Author" with slug "bdd-retrieve-author"
    When I GET the v2 admin endpoint "contentdb/admin/authors/{saved.author_uid}/"
    Then the response status should be 200
    And the response field "name" should equal "BDD Retrieve Author"
    And the response field "slug" should equal "bdd-retrieve-author"

  Scenario: Retrieve non-existent author returns 404
    When I GET the v2 admin endpoint "contentdb/admin/authors/00000000-0000-0000-0000-000000000000/"
    Then the response status should be 404

  # --- Update ---

  Scenario: Update author name and slug
    Given I ensure contentdb author with slug "bdd-updated-slug" is cleaned up
    Given I create a test contentdb author "BDD Update Author" with slug "bdd-update-author"
    When I PATCH the v2 admin endpoint "contentdb/admin/authors/{saved.author_uid}/" with body
      """
      {"name": "BDD Updated Name", "slug": "bdd-updated-slug"}
      """
    Then the response status should be 200
    And the response field "name" should equal "BDD Updated Name"
    And the response field "slug" should equal "bdd-updated-slug"

  Scenario: Update author active status
    Given I create a test contentdb author "BDD Toggle Author" with slug "bdd-toggle-author"
    When I PATCH the v2 admin endpoint "contentdb/admin/authors/{saved.author_uid}/" with body
      """
      {"is_active": false}
      """
    Then the response status should be 200
    And the response field "is_active" should be false

  # --- Delete ---

  Scenario: Delete author without reassignment
    Given I create a test contentdb author "BDD Delete No Reassign" with slug "bdd-delete-no-reassign"
    When I DELETE the v2 admin endpoint "contentdb/admin/authors/{saved.author_uid}/" with body
      """
      {"reassign_to": null}
      """
    Then the response status should be 204

  Scenario: Delete author with reassignment
    Given I create a test contentdb author "BDD Delete Source" with slug "bdd-delete-source"
    And I create a test contentdb author "BDD Reassign Target" with slug "bdd-reassign-target"
    When I DELETE the v2 admin endpoint "contentdb/admin/authors/{saved.author_uid_1}/" with body
      """
      {"reassign_to": "{saved.author_uid_2}"}
      """
    Then the response status should be 204
