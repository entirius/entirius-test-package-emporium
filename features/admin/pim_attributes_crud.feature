@admin @pim-admin @v2 @crud @attributes
Feature: PIM Admin API -- Attribute CRUD
  As an admin user
  I want to create, read, update, and delete attributes
  So that I can manage selectable values for product features

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- List ---

  Scenario: List attributes returns paginated structure
    When I GET the v2 admin endpoint "pim/admin/attributes/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | results  |
    And the results count should be greater than 0

  # --- Full CRUD Lifecycle ---

  Scenario: Attribute CRUD lifecycle (create, retrieve, update, delete)
    # Setup: ensure parent feature exists
    Given I ensure v2 admin resource "pim/admin/attributes/bdd-attr-feat/bdd-red/" is deleted
    Given I ensure v2 admin resource "pim/admin/features/bdd-attr-feat/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-attr-feat", "name_t9n": {"en": "BDD Attr Feature"}, "feature_type": 7}
      """
    Then the response status should be 201
    # Create attribute
    When I POST to the v2 admin endpoint "pim/admin/attributes/" with body
      """
      {
        "feature_idx": "bdd-attr-feat",
        "idx": "bdd-red",
        "name_t9n": {"en": "BDD Red", "pl": "BDD Czerwony"},
        "display_order": 100
      }
      """
    Then the response status should be 201
    And the response field "idx" should equal "bdd-red"
    And the response field "feature_idx" should equal "bdd-attr-feat"
    And the response field "name" should not be null
    And the response field "display_order" should equal integer 100
    # Retrieve by composite key
    When I GET the v2 admin endpoint "pim/admin/attributes/bdd-attr-feat/bdd-red/"
    Then the response status should be 200
    And the response field "idx" should equal "bdd-red"
    And the response field "feature_idx" should equal "bdd-attr-feat"
    And the response field "pk" should not be null
    # Update
    When I PATCH the v2 admin endpoint "pim/admin/attributes/bdd-attr-feat/bdd-red/" with body
      """
      {
        "name_t9n": {"en": "BDD Red Updated"},
        "display_order": 50
      }
      """
    Then the response status should be 200
    And the response field "display_order" should equal integer 50
    # Verify update persisted
    When I GET the v2 admin endpoint "pim/admin/attributes/bdd-attr-feat/bdd-red/"
    Then the response status should be 200
    And the response field "display_order" should equal integer 50
    # Delete attribute
    When I DELETE the v2 admin endpoint "pim/admin/attributes/bdd-attr-feat/bdd-red/"
    Then the response status should be 200
    # Verify deleted
    When I GET the v2 admin endpoint "pim/admin/attributes/bdd-attr-feat/bdd-red/"
    Then the response status should be 404
    # Cleanup parent feature
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-attr-feat/"
    Then the response status should be 200

  # --- Attribute with Group ---

  Scenario: Create attribute with group assignment
    Given I ensure v2 admin resource "pim/admin/attributes/bdd-grp-feat/bdd-blue/" is deleted
    Given I ensure v2 admin resource "pim/admin/features/bdd-grp-feat/" is deleted
    Given I ensure v2 admin resource "pim/admin/attributes-groups/bdd-cool-colors/" is deleted
    # Create group
    When I POST to the v2 admin endpoint "pim/admin/attributes-groups/" with body
      """
      {"idx": "bdd-cool-colors", "name_t9n": {"en": "Cool Colors"}}
      """
    Then the response status should be 201
    # Create feature
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-grp-feat", "name_t9n": {"en": "Group Feature"}, "feature_type": 7}
      """
    Then the response status should be 201
    # Create attribute with group
    When I POST to the v2 admin endpoint "pim/admin/attributes/" with body
      """
      {
        "feature_idx": "bdd-grp-feat",
        "idx": "bdd-blue",
        "name_t9n": {"en": "Blue"},
        "group_idx": "bdd-cool-colors"
      }
      """
    Then the response status should be 201
    And the response field "group_idx" should equal "bdd-cool-colors"
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/attributes/bdd-grp-feat/bdd-blue/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-grp-feat/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/attributes-groups/bdd-cool-colors/"
    Then the response status should be 200

  # --- Error Cases ---

  Scenario: Retrieve non-existent attribute returns 404
    When I GET the v2 admin endpoint "pim/admin/attributes/nonexistent/nonexistent/"
    Then the response status should be 404
