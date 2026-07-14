@admin @pim-admin @v2 @crud @new-endpoints
Feature: PIM Admin API -- New Endpoints (Feature Set Edit)
  As an admin user
  I want to use the new reorder and filter endpoints
  So that I can manage feature sets, features, and attributes effectively

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # ==========================================================================
  # T3: exclude_feature_set filter on features list
  # ==========================================================================

  Scenario: Filter features excluding those in a feature set
    # Setup: create feature, set, and add feature to set
    Given I ensure v2 admin resource "pim/admin/feature-sets/bdd-excl-set/" is deleted
    Given I ensure v2 admin resource "pim/admin/features/bdd-excl-feat-1/" is deleted
    Given I ensure v2 admin resource "pim/admin/features/bdd-excl-feat-2/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-excl-feat-1", "name_t9n": {"en": "Excl Feature 1"}, "feature_type": 1}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-excl-feat-2", "name_t9n": {"en": "Excl Feature 2"}, "feature_type": 1}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/" with body
      """
      {"idx": "bdd-excl-set", "name": "Exclusion Test Set"}
      """
    Then the response status should be 201
    # Add feat-1 to the set
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/bdd-excl-set/features/" with body
      """
      {"features": [{"feature_idx": "bdd-excl-feat-1"}]}
      """
    Then the response status should be 201
    # Filter with exclude_feature_set: feat-1 should NOT appear, feat-2 SHOULD
    When I GET the v2 admin endpoint "pim/admin/features/" with params
      | param              | value        |
      | exclude_feature_set | bdd-excl-set |
      | search             | bdd-excl     |
    Then the response status should be 200
    And the results should not contain an item with "idx" equal to "bdd-excl-feat-1"
    And the results should contain an item with "idx" equal to "bdd-excl-feat-2"
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-excl-set/features/" with body
      """
      {"feature_idxs": ["bdd-excl-feat-1"]}
      """
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-excl-set/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-excl-feat-1/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-excl-feat-2/"
    Then the response status should be 200

  # ==========================================================================
  # T1/T2: attributes_group FK on FeatureInFeatureSet
  # ==========================================================================

  Scenario: Add feature to set with attributes_group assignment
    # Setup
    Given I ensure v2 admin resource "pim/admin/feature-sets/bdd-grp-assign/" is deleted
    Given I ensure v2 admin resource "pim/admin/features/bdd-grp-assign-feat/" is deleted
    Given I ensure v2 admin resource "pim/admin/attributes-groups/bdd-grp-general/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/attributes-groups/" with body
      """
      {"idx": "bdd-grp-general", "name_t9n": {"en": "General"}}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-grp-assign-feat", "name_t9n": {"en": "Group Assign Feature"}, "feature_type": 3}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/" with body
      """
      {"idx": "bdd-grp-assign", "name": "Group Assignment Test"}
      """
    Then the response status should be 201
    # Add feature with attributes_group_idx
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/bdd-grp-assign/features/" with body
      """
      {"features": [{"feature_idx": "bdd-grp-assign-feat", "position": 100, "attributes_group_idx": "bdd-grp-general"}]}
      """
    Then the response status should be 201
    # Verify group info in response
    When I GET the v2 admin endpoint "pim/admin/feature-sets/bdd-grp-assign/features/"
    Then the response status should be 200
    And the results count should be greater than 0
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-grp-assign/features/" with body
      """
      {"feature_idxs": ["bdd-grp-assign-feat"]}
      """
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-grp-assign/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-grp-assign-feat/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/attributes-groups/bdd-grp-general/"
    Then the response status should be 200

  # ==========================================================================
  # T4: Reorder features in feature set
  # ==========================================================================

  Scenario: Reorder features within a feature set
    # Setup
    Given I ensure v2 admin resource "pim/admin/feature-sets/bdd-reorder-set/" is deleted
    Given I ensure v2 admin resource "pim/admin/features/bdd-reorder-a/" is deleted
    Given I ensure v2 admin resource "pim/admin/features/bdd-reorder-b/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-reorder-a", "name_t9n": {"en": "Reorder A"}, "feature_type": 1}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-reorder-b", "name_t9n": {"en": "Reorder B"}, "feature_type": 1}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/" with body
      """
      {"idx": "bdd-reorder-set", "name": "Reorder Test Set"}
      """
    Then the response status should be 201
    # Add both features
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/bdd-reorder-set/features/" with body
      """
      {"features": [{"feature_idx": "bdd-reorder-a", "position": 100}, {"feature_idx": "bdd-reorder-b", "position": 200}]}
      """
    Then the response status should be 201
    # Reorder: swap positions
    When I PATCH the v2 admin endpoint "pim/admin/feature-sets/bdd-reorder-set/features/reorder/" with body
      """
      {"features": [{"feature_idx": "bdd-reorder-a", "position": 200}, {"feature_idx": "bdd-reorder-b", "position": 100}]}
      """
    Then the response status should be 200
    And the response field "reordered" should equal integer 2
    # Verify new order
    When I GET the v2 admin endpoint "pim/admin/feature-sets/bdd-reorder-set/features/"
    Then the response status should be 200
    And the results count should be greater than 0
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-reorder-set/features/" with body
      """
      {"feature_idxs": ["bdd-reorder-a", "bdd-reorder-b"]}
      """
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-reorder-set/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-reorder-a/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-reorder-b/"
    Then the response status should be 200

  Scenario: Reorder features in non-existent set returns 404
    When I PATCH the v2 admin endpoint "pim/admin/feature-sets/does-not-exist/features/reorder/" with body
      """
      {"features": [{"feature_idx": "color", "position": 1}]}
      """
    Then the response status should be 404

  # ==========================================================================
  # T11: Attribute reorder endpoint
  # ==========================================================================

  Scenario: Reorder attributes (batch display_order update)
    # Setup: create feature + two attributes
    Given I ensure v2 admin resource "pim/admin/attributes/bdd-reorder-feat/bdd-opt-a/" is deleted
    Given I ensure v2 admin resource "pim/admin/attributes/bdd-reorder-feat/bdd-opt-b/" is deleted
    Given I ensure v2 admin resource "pim/admin/features/bdd-reorder-feat/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {"idx": "bdd-reorder-feat", "name_t9n": {"en": "Reorder Attr Feature"}, "feature_type": 7}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/attributes/" with body
      """
      {"feature_idx": "bdd-reorder-feat", "idx": "bdd-opt-a", "name_t9n": {"en": "Option A"}, "display_order": 100}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/attributes/" with body
      """
      {"feature_idx": "bdd-reorder-feat", "idx": "bdd-opt-b", "name_t9n": {"en": "Option B"}, "display_order": 200}
      """
    Then the response status should be 201
    # Reorder: swap display_order
    When I PATCH the v2 admin endpoint "pim/admin/attributes/reorder/" with body
      """
      {"items": [{"feature_idx": "bdd-reorder-feat", "idx": "bdd-opt-a", "display_order": 200}, {"feature_idx": "bdd-reorder-feat", "idx": "bdd-opt-b", "display_order": 100}]}
      """
    Then the response status should be 200
    And the response field "reordered" should equal integer 2
    # Verify new order: opt-b should now have display_order 100
    When I GET the v2 admin endpoint "pim/admin/attributes/bdd-reorder-feat/bdd-opt-b/"
    Then the response status should be 200
    And the response field "display_order" should equal integer 100
    # Verify opt-a has display_order 200
    When I GET the v2 admin endpoint "pim/admin/attributes/bdd-reorder-feat/bdd-opt-a/"
    Then the response status should be 200
    And the response field "display_order" should equal integer 200
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/attributes/bdd-reorder-feat/bdd-opt-a/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/attributes/bdd-reorder-feat/bdd-opt-b/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/features/bdd-reorder-feat/"
    Then the response status should be 200

  Scenario: Reorder attributes with non-existent attribute returns 404
    When I PATCH the v2 admin endpoint "pim/admin/attributes/reorder/" with body
      """
      {"items": [{"feature_idx": "nonexistent", "idx": "nonexistent", "display_order": 1}]}
      """
    Then the response status should be 404

  Scenario: Reorder attributes with empty items returns 400
    When I PATCH the v2 admin endpoint "pim/admin/attributes/reorder/" with body
      """
      {"items": []}
      """
    Then the response status should be 400

  # ==========================================================================
  # Auth tests for new endpoints
  # ==========================================================================

  Scenario: Feature sets endpoint requires authentication
    When I GET the v2 admin endpoint "pim/admin/feature-sets/" without auth
    Then the response status should be 401
