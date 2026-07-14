@admin @pim-admin @v2 @crud @feature-sets
Feature: PIM Admin API -- Feature Set CRUD
  As an admin user
  I want to create, read, update, and delete feature sets
  So that I can organize features into reusable groups

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- List ---

  Scenario: List feature sets returns paginated structure
    When I GET the v2 admin endpoint "pim/admin/feature-sets/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | results  |
    And the results count should be greater than 0

  Scenario: List feature sets for a channel returns results
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/feature-sets/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | results  |

  # --- Full CRUD Lifecycle ---

  Scenario: Feature set CRUD lifecycle (create, retrieve, update, delete)
    # Cleanup
    Given I ensure v2 admin resource "pim/admin/feature-sets/bdd-test-set/" is deleted
    # Create
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/" with body
      """
      {
        "idx": "bdd-test-set",
        "name": "BDD Test Set",
        "desc": "Feature set for BDD testing",
        "is_default": false
      }
      """
    Then the response status should be 201
    And the response field "idx" should equal "bdd-test-set"
    And the response field "name" should equal "BDD Test Set"
    And the response field "desc" should equal "Feature set for BDD testing"
    And the response field "is_default" should be false
    And the response field "feature_count" should equal integer 0
    # Retrieve
    When I GET the v2 admin endpoint "pim/admin/feature-sets/bdd-test-set/"
    Then the response status should be 200
    And the response field "idx" should equal "bdd-test-set"
    And the response field "pk" should not be null
    # Update
    When I PATCH the v2 admin endpoint "pim/admin/feature-sets/bdd-test-set/" with body
      """
      {
        "name": "BDD Test Set Updated",
        "desc": "Updated description"
      }
      """
    Then the response status should be 200
    And the response field "name" should equal "BDD Test Set Updated"
    And the response field "desc" should equal "Updated description"
    # Delete
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-test-set/"
    Then the response status should be 200
    # Verify deleted
    When I GET the v2 admin endpoint "pim/admin/feature-sets/bdd-test-set/"
    Then the response status should be 404

  # --- Feature Management in Sets ---

  Scenario: Add and remove features from a feature set
    # Setup: create set and feature
    Given I ensure v2 admin resource "pim/admin/feature-sets/bdd-feat-mgmt/" is deleted
    Given I ensure v2 admin resource "pim/admin/features/bdd-set-feat-1/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-set-feat-1", "name_t9n": {"en": "Set Feature 1"}, "feature_type": 1}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/" with body
      """
      {"idx": "bdd-feat-mgmt", "name": "Feature Management Test"}
      """
    Then the response status should be 201
    # Add feature to set
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/bdd-feat-mgmt/features/" with body
      """
      {"features": [{"feature_idx": "bdd-set-feat-1", "position": 100}]}
      """
    Then the response status should be 201
    # Verify feature is in set
    When I GET the v2 admin endpoint "pim/admin/feature-sets/bdd-feat-mgmt/features/"
    Then the response status should be 200
    And the results count should be greater than 0
    # Remove feature from set
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-feat-mgmt/features/" with body
      """
      {"feature_idxs": ["bdd-set-feat-1"]}
      """
    Then the response status should be 200
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-feat-mgmt/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-set-feat-1/"
    Then the response status should be 200

  # --- Error Cases ---

  Scenario: Create feature set with duplicate idx returns 400
    Given I ensure v2 admin resource "pim/admin/feature-sets/bdd-dup-set/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/" with body
      """
      {"idx": "bdd-dup-set", "name": "Dup Set"}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/" with body
      """
      {"idx": "bdd-dup-set", "name": "Dup Set 2"}
      """
    Then the response status should be 400
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-dup-set/"
    Then the response status should be 200

  Scenario: Retrieve non-existent feature set returns 404
    When I GET the v2 admin endpoint "pim/admin/feature-sets/does-not-exist-xyz/"
    Then the response status should be 404
