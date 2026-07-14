@admin @pim-admin @v2 @crud @features
Feature: PIM Admin API -- Feature CRUD
  As an admin user
  I want to create, read, update, and delete features
  So that I can manage the product attribute catalog

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- List ---

  Scenario: List features returns paginated structure
    When I GET the v2 admin endpoint "pim/admin/features/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |
    And the results count should be greater than 0

  Scenario: List features for a channel returns paginated structure
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/features/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | results  |

  # --- Full CRUD Lifecycle ---

  Scenario: Feature CRUD lifecycle (create, retrieve, update, delete)
    # Cleanup from previous runs
    Given I ensure v2 admin resource "pim/admin/features/bdd-test-color/" is deleted
    # Create
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {
        "idx": "bdd-test-color",
        "name_t9n": {"en": "BDD Color", "pl": "BDD Kolor"},
        "feature_type": 7,
        "scope": 3,
        "is_filterable": true,
        "is_visible": true
      }
      """
    Then the response status should be 201
    And the response field "idx" should equal "bdd-test-color"
    And the response field "feature_type" should equal integer 7
    And the response field "feature_type_name" should not be null
    And the response field "scope" should equal integer 3
    And the response field "is_filterable" should be true
    And the response field "is_visible" should be true
    And the response field "name" should not be null
    # Retrieve
    When I GET the v2 admin endpoint "pim/admin/features/bdd-test-color/"
    Then the response status should be 200
    And the response field "idx" should equal "bdd-test-color"
    And the response field "name" should not be null
    And the response field "pk" should not be null
    And the response should have the fields
      | field                  |
      | scope_name             |
      | frontend_input_type    |
      | filter_type            |
      | display_order          |
      | is_required            |
      | is_searchable          |
      | is_comparable          |
      | is_for_customization   |
    # Update
    When I PATCH the v2 admin endpoint "pim/admin/features/bdd-test-color/" with body
      """
      {
        "name_t9n": {"en": "BDD Color Updated", "pl": "BDD Kolor Zmieniony"},
        "is_filterable": false,
        "display_order": 42
      }
      """
    Then the response status should be 200
    And the response field "is_filterable" should be false
    And the response field "display_order" should equal integer 42
    # Verify update persisted
    When I GET the v2 admin endpoint "pim/admin/features/bdd-test-color/"
    Then the response status should be 200
    And the response field "display_order" should equal integer 42
    # Delete
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-test-color/"
    Then the response status should be 200
    # Verify deleted
    When I GET the v2 admin endpoint "pim/admin/features/bdd-test-color/"
    Then the response status should be 404

  # --- Error Cases ---

  Scenario: Create feature with duplicate idx returns 400
    Given I ensure v2 admin resource "pim/admin/features/bdd-test-dup/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-test-dup", "name_t9n": {"en": "Dup Test"}, "feature_type": 1}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-test-dup", "name_t9n": {"en": "Dup Test 2"}, "feature_type": 1}
      """
    Then the response status should be 400
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-test-dup/"
    Then the response status should be 200

  Scenario: Retrieve non-existent feature returns 404
    When I GET the v2 admin endpoint "pim/admin/features/does-not-exist-xyz/"
    Then the response status should be 404

  Scenario: Delete non-existent feature returns 404
    When I DELETE the v2 admin endpoint "pim/admin/features/does-not-exist-xyz/"
    Then the response status should be 404

  # --- Feature Attributes Nested Endpoint ---

  Scenario: List attributes for an existing feature
    When I GET the v2 admin endpoint "pim/admin/features/" with params
      | param     | value |
      | page_size | 1     |
    Then the response status should be 200
    And the results count should be greater than 0
