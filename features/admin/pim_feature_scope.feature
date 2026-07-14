@admin @pim-admin @v2 @feature-scope
Feature: PIM Admin API -- Feature Scope Protection
  As an admin user
  I should not be able to modify or delete system features
  And I should not be able to create features with deprecated scopes

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- SYSTEM Feature Protection ---

  Scenario: Cannot create feature with SYSTEM scope
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {
        "idx": "bdd-system-test",
        "name_t9n": {"en": "Should Fail"},
        "scope": 1
      }
      """
    Then the response status should be 400

  Scenario: Cannot delete system feature
    When I DELETE the v2 admin endpoint "pim/admin/features/name/"
    Then the response status should be 400

  Scenario: Cannot change system feature type
    When I PATCH the v2 admin endpoint "pim/admin/features/name/" with body
      """
      {"feature_type": 2}
      """
    Then the response status should be 400

  Scenario: Can update system feature name translations
    When I PATCH the v2 admin endpoint "pim/admin/features/name/" with body
      """
      {"name_t9n": {"en": "Name", "pl": "Nazwa"}}
      """
    Then the response status should be 200

  Scenario: Cannot change feature scope to SYSTEM
    Given I ensure v2 admin resource "pim/admin/features/bdd-scope-test/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {
        "idx": "bdd-scope-test",
        "name_t9n": {"en": "Scope Test"},
        "scope": 3
      }
      """
    Then the response status should be 201
    When I PATCH the v2 admin endpoint "pim/admin/features/bdd-scope-test/" with body
      """
      {"scope": 1}
      """
    Then the response status should be 400
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-scope-test/"

  Scenario: Feature response includes is_system flag
    When I GET the v2 admin endpoint "pim/admin/features/name/"
    Then the response status should be 200
    And the response field "is_system" should be true
