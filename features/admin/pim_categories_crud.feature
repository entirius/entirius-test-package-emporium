@admin @pim-admin @v2 @crud @categories
Feature: PIM Admin API -- Category CRUD
  As an admin user
  I want to create, read, update, and delete categories
  So that I can organize the product catalog hierarchy

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- List ---

  Scenario: Categories list returns paginated structure with filters
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |
    And the results count should be greater than 0

  Scenario: Categories list supports root_only filter
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with params
      | param     | value |
      | root_only | true  |
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: Categories list supports is_active filter
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with params
      | param     | value |
      | is_active | true  |
    Then the response status should be 200

  # --- Full CRUD Lifecycle ---

  Scenario: Category CRUD lifecycle (create, retrieve, update, delete)
    # Cleanup
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/categories/bdd-test-cat/" is deleted
    # Create
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with body
      """
      {
        "idx": "bdd-test-cat",
        "name_t9n": {"en": "BDD Test Category", "pl": "BDD Kategoria Testowa"},
        "description_t9n": {"en": "A test category for BDD"},
        "meta_title_t9n": {"en": "BDD Test"},
        "meta_description_t9n": {"en": "BDD test category meta"},
        "is_active": true,
        "is_in_menu": true,
        "position": 999
      }
      """
    Then the response status should be 201
    And the response field "idx" should equal "bdd-test-cat"
    And the response field "is_active" should be true
    And the response field "is_in_menu" should be true
    And the response field "name" should not be null
    And the response field "name_t9n" should be a dict
    And the response field "description_t9n" should be a dict
    And the response field "meta_title_t9n" should be a dict
    And the response field "url_key_t9n" should be a dict
    And the response field "breadcrumb_path" should not be null
    And the response field "tree_deep" should equal integer 0
    And the response field "product_count" should equal integer 0
    And the response field "subcategory_count" should equal integer 0
    And the response field "parent_category" should be null
    # Retrieve
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-test-cat/"
    Then the response status should be 200
    And the response field "idx" should equal "bdd-test-cat"
    And the response field "pk" should not be null
    And the response should have the fields
      | field               |
      | name_t9n            |
      | description_t9n     |
      | meta_title_t9n      |
      | meta_description_t9n|
      | url_key_t9n         |
      | breadcrumb_path     |
      | tree_deep           |
      | position            |
    # Update
    When I PATCH the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-test-cat/" with body
      """
      {
        "name_t9n": {"en": "BDD Updated Category"},
        "is_active": false,
        "position": 500
      }
      """
    Then the response status should be 200
    And the response field "is_active" should be false
    # Verify update persisted
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-test-cat/"
    Then the response status should be 200
    And the response field "is_active" should be false
    And the response nested field "name_t9n.en" should equal "BDD Updated Category"
    # Delete
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-test-cat/"
    Then the response status should be 200
    # Verify deleted
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-test-cat/"
    Then the response status should be 404

  # --- Subcategory (parent-child relationship) ---

  Scenario: Create subcategory with parent reference
    # Cleanup
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/categories/bdd-sub-child/" is deleted
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/categories/bdd-sub-parent/" is deleted
    # Create parent
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with body
      """
      {
        "idx": "bdd-sub-parent",
        "name_t9n": {"en": "BDD Parent"},
        "is_active": true,
        "is_in_menu": true
      }
      """
    Then the response status should be 201
    And the response field "tree_deep" should equal integer 0
    # Create child
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with body
      """
      {
        "idx": "bdd-sub-child",
        "name_t9n": {"en": "BDD Child"},
        "parent_category_idx": "bdd-sub-parent",
        "is_active": true,
        "is_in_menu": true
      }
      """
    Then the response status should be 201
    And the response field "tree_deep" should equal integer 1
    And the response field "parent_category" should not be null
    And the response field "parent_category_idx" should equal "bdd-sub-parent"
    # Verify parent has subcategory count
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-sub-parent/"
    Then the response status should be 200
    And the response field "subcategory_count" should equal integer 1
    # Delete child first, then parent
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-sub-child/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-sub-parent/"
    Then the response status should be 200

  # --- Cascade Delete ---

  Scenario: Delete category cascades subcategories
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/categories/bdd-cascade-child/" is deleted
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/categories/bdd-cascade-parent/" is deleted
    # Create parent + child
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with body
      """
      {"idx": "bdd-cascade-parent", "name_t9n": {"en": "Cascade Parent"}, "is_active": true, "is_in_menu": true}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with body
      """
      {"idx": "bdd-cascade-child", "name_t9n": {"en": "Cascade Child"}, "parent_category_idx": "bdd-cascade-parent", "is_active": true, "is_in_menu": true}
      """
    Then the response status should be 201
    # Delete parent (cascades child)
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-cascade-parent/"
    Then the response status should be 200
    # Child should also be gone
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-cascade-child/"
    Then the response status should be 404

  # --- Error Cases ---

  Scenario: Create category with duplicate idx returns 400
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/categories/bdd-dup-cat/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with body
      """
      {"idx": "bdd-dup-cat", "name_t9n": {"en": "Dup Cat"}, "is_active": true, "is_in_menu": true}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with body
      """
      {"idx": "bdd-dup-cat", "name_t9n": {"en": "Dup Cat 2"}, "is_active": true, "is_in_menu": true}
      """
    Then the response status should be 400
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-dup-cat/"
    Then the response status should be 200

  Scenario: Retrieve non-existent category returns 404
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/does-not-exist-xyz/"
    Then the response status should be 404
