@admin @faq @faq-groups @v2 @crud
Feature: FAQ Admin API -- Group CRUD
  As an admin user
  I want to create, read, update, and delete FAQ groups
  So that I can manage thematic collections of FAQ items

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- Authentication ---

  Scenario: Unauthenticated request to groups returns 401
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/groups/" without auth
    Then the response status should be 401
    And the error response should have error code "AUTHENTICATION_REQUIRED"
    And the error response should have a debug_id

  Scenario: Non-admin user on groups returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/groups/"
    Then the response status should be 403
    And the error response should have error code "PERMISSION_DENIED"
    And the error response should have a debug_id

  # --- List ---

  Scenario: Groups list returns paginated structure
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/groups/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Groups list contains fixture groups
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/groups/"
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "idx" equal to "shipping"

  # --- Full CRUD Lifecycle ---

  Scenario: Group CRUD lifecycle (create, retrieve, update, delete)
    # Cleanup from previous runs
    Given I ensure faq group with idx "bdd-test-group" is cleaned up
    # Create
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/" with body
      """
      {
        "idx": "bdd-test-group",
        "name": "BDD Test Group",
        "position": 99,
        "is_active": true
      }
      """
    Then the response status should be 201
    And the response field "idx" should equal "bdd-test-group"
    And the response field "name" should equal "BDD Test Group"
    And the response field "position" should equal integer 99
    And the response field "is_active" should be true
    And the response field "item_count" should equal integer 0
    And the response field "translations" should be a list
    Then I save the response field "id" as "saved.group_id"
    # Retrieve
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-test-group/"
    Then the response status should be 200
    And the response should have the fields
      | field       |
      | id          |
      | idx         |
      | name        |
      | translations|
      | channel_ids |
      | position    |
      | is_active   |
      | item_count  |
    And the response field "idx" should equal "bdd-test-group"
    And the response field "name" should equal "BDD Test Group"
    # Update
    When I PATCH the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-test-group/" with body
      """
      {
        "name": "BDD Group Updated",
        "is_active": false
      }
      """
    Then the response status should be 200
    And the response field "name" should equal "BDD Group Updated"
    And the response field "is_active" should be false
    # Verify update persisted
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-test-group/"
    Then the response status should be 200
    And the response field "name" should equal "BDD Group Updated"
    And the response field "is_active" should be false
    # Delete
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-test-group/"
    Then the response status should be 204
    # Verify deleted
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-test-group/"
    Then the response status should be 404

  # --- Reorder ---

  Scenario: Reorder groups updates positions
    Given I ensure faq group with idx "bdd-reorder-a" is cleaned up
    Given I ensure faq group with idx "bdd-reorder-b" is cleaned up
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/" with body
      """
      {"idx": "bdd-reorder-a", "name": "BDD Reorder A", "position": 10}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/" with body
      """
      {"idx": "bdd-reorder-b", "name": "BDD Reorder B", "position": 20}
      """
    Then the response status should be 201
    When I PATCH the v2 admin endpoint "faq/admin/{channel_idx}/groups/reorder/" with body
      """
      {"ordered_idxs": ["bdd-reorder-b", "bdd-reorder-a"]}
      """
    Then the response status should be 200
    And the response field "status" should equal "ok"
    # Cleanup
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-reorder-a/"
    Then the response status should be 204
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-reorder-b/"
    Then the response status should be 204

  # --- Group Translations ---

  Scenario: Create, update, and delete a group translation
    Given I ensure faq group with idx "bdd-t9n-group" is cleaned up
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/" with body
      """
      {"idx": "bdd-t9n-group", "name": "BDD Translation Group"}
      """
    Then the response status should be 201
    # Create translation
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-t9n-group/translations/" with body
      """
      {"language": "pl", "name": "BDD Grupa Tłumaczona"}
      """
    Then the response status should be 201
    And the response field "language" should equal "pl"
    And the response field "name" should equal "BDD Grupa Tłumaczona"
    # Update translation
    When I PATCH the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-t9n-group/translations/pl/" with body
      """
      {"name": "BDD Grupa Zmieniona"}
      """
    Then the response status should be 200
    And the response field "name" should equal "BDD Grupa Zmieniona"
    # Verify in translations list
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-t9n-group/translations/"
    Then the response status should be 200
    # Delete translation
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-t9n-group/translations/pl/"
    Then the response status should be 204
    # Cleanup group
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-t9n-group/"
    Then the response status should be 204

  # --- Error Cases ---

  Scenario: Create group with duplicate idx returns 400
    Given I ensure faq group with idx "bdd-dup-group" is cleaned up
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/" with body
      """
      {"idx": "bdd-dup-group", "name": "First Group"}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/" with body
      """
      {"idx": "bdd-dup-group", "name": "Duplicate Group"}
      """
    Then the response status should be 400
    # Cleanup
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-dup-group/"
    Then the response status should be 204

  Scenario: Retrieve non-existent group returns 404
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/groups/does-not-exist-xyz/"
    Then the response status should be 404

  Scenario: Delete non-existent group returns 404
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/groups/does-not-exist-xyz/"
    Then the response status should be 404
