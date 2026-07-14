@admin @agreements @v2 @crud
Feature: Agreements Admin API -- Definition & Version CRUD
  As an admin user
  I want to create, update, and manage agreement definitions and versions
  So that I can maintain consent agreements for the platform

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- Definition CRUD Lifecycle ---

  Scenario: Definition CRUD lifecycle (create, retrieve, update, delete)
    # Cleanup from previous runs
    Given I ensure v2 admin resource "agreements/admin/definitions/bdd-test-agreement/" is deleted
    # Create
    When I POST to the v2 admin endpoint "agreements/admin/definitions/" with body
      """
      {
        "slug": "bdd-test-agreement",
        "name": "BDD Test Agreement",
        "category": "informational",
        "consent_channel": "general",
        "sort_order": 99,
        "is_active": true
      }
      """
    Then the response status should be 201
    And the response field "slug" should equal "bdd-test-agreement"
    And the response field "name" should equal "BDD Test Agreement"
    And the response field "category" should equal "informational"
    And the response field "is_active" should be true
    # Retrieve
    When I GET the v2 admin endpoint "agreements/admin/definitions/bdd-test-agreement/"
    Then the response status should be 200
    And the response field "slug" should equal "bdd-test-agreement"
    # Update
    When I PATCH the v2 admin endpoint "agreements/admin/definitions/bdd-test-agreement/" with body
      """
      {
        "name": "BDD Test Agreement Updated",
        "sort_order": 50
      }
      """
    Then the response status should be 200
    And the response field "name" should equal "BDD Test Agreement Updated"
    # Soft-delete
    When I DELETE the v2 admin endpoint "agreements/admin/definitions/bdd-test-agreement/"
    Then the response status should be 204
    # Verify soft-deleted
    When I GET the v2 admin endpoint "agreements/admin/definitions/bdd-test-agreement/"
    Then the response status should be 200
    And the response field "is_active" should be false

  # --- Version Lifecycle ---

  Scenario: Version lifecycle (create draft, publish)
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user
    Given I ensure v2 admin resource "agreements/admin/definitions/bdd-version-lifecycle/" is deleted
    When I POST to the v2 admin endpoint "agreements/admin/definitions/" with body
      """
      {
        "slug": "bdd-version-lifecycle",
        "name": "BDD Version Test",
        "category": "informational",
        "consent_channel": "general",
        "is_active": true
      }
      """
    Then the response status should be 201
    # Create version
    When I POST to the v2 admin endpoint "agreements/admin/definitions/bdd-version-lifecycle/versions/" with body
      """
      {
        "summary_t9n": {
          "en": "I accept the BDD test agreement",
          "pl": "Akceptuję umowę testową BDD"
        }
      }
      """
    Then the response status should be 201
    And the response field "is_current" should be false
    Then I save the response field "id" as "saved.version_id"
    # Publish
    When I POST to the v2 admin endpoint "agreements/admin/versions/{saved.version_id}/publish/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "is_current" should be true
    # List versions
    When I GET the v2 admin endpoint "agreements/admin/definitions/bdd-version-lifecycle/versions/"
    Then the response status should be 200
    And the results count should be greater than 0

  # --- Consent Log ---

  Scenario: Admin can view consent log
    When I GET the v2 admin endpoint "agreements/admin/consents/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  # --- Cleanup ---

  Scenario: Final cleanup of BDD test definition
    Given I ensure v2 admin resource "agreements/admin/definitions/bdd-test-agreement/" is deleted
