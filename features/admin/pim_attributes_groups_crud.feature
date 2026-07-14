@admin @pim-admin @v2 @crud @attributes-groups
Feature: PIM Admin API -- Attributes Group CRUD
  As an admin user
  I want to create, read, update, and delete attributes groups
  So that I can organize attributes into logical clusters

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- List ---

  Scenario: List attributes groups returns paginated structure
    When I GET the v2 admin endpoint "pim/admin/attributes-groups/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | results  |

  Scenario: List attributes groups for a channel
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/attributes-groups/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | results  |

  # --- Full CRUD Lifecycle ---

  Scenario: Attributes group CRUD lifecycle (create, retrieve, update, delete)
    # Cleanup
    Given I ensure v2 admin resource "pim/admin/attributes-groups/bdd-test-grp/" is deleted
    # Create
    When I POST to the v2 admin endpoint "pim/admin/attributes-groups/" with body
      """
      {
        "idx": "bdd-test-grp",
        "name_t9n": {"en": "BDD Test Group", "pl": "BDD Grupa Testowa"}
      }
      """
    Then the response status should be 201
    And the response field "idx" should equal "bdd-test-grp"
    And the response field "name" should not be null
    And the response field "pk" should not be null
    And the response field "attribute_count" should equal integer 0
    # Retrieve
    When I GET the v2 admin endpoint "pim/admin/attributes-groups/bdd-test-grp/"
    Then the response status should be 200
    And the response field "idx" should equal "bdd-test-grp"
    # Channel-scoped retrieve
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/attributes-groups/bdd-test-grp/"
    Then the response status should be 200
    And the response field "idx" should equal "bdd-test-grp"
    # Update
    When I PATCH the v2 admin endpoint "pim/admin/attributes-groups/bdd-test-grp/" with body
      """
      {
        "name_t9n": {"en": "BDD Group Updated", "pl": "BDD Grupa Zmieniona"}
      }
      """
    Then the response status should be 200
    # Verify update
    When I GET the v2 admin endpoint "pim/admin/attributes-groups/bdd-test-grp/"
    Then the response status should be 200
    And the response field "name" should not be null
    # Delete
    When I DELETE the v2 admin endpoint "pim/admin/attributes-groups/bdd-test-grp/"
    Then the response status should be 200
    # Verify deleted
    When I GET the v2 admin endpoint "pim/admin/attributes-groups/bdd-test-grp/"
    Then the response status should be 404

  # --- Error Cases ---

  Scenario: Create attributes group with duplicate idx returns 400
    Given I ensure v2 admin resource "pim/admin/attributes-groups/bdd-dup-grp/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/attributes-groups/" with body
      """
      {"idx": "bdd-dup-grp", "name_t9n": {"en": "Dup Group"}}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/attributes-groups/" with body
      """
      {"idx": "bdd-dup-grp", "name_t9n": {"en": "Dup Group 2"}}
      """
    Then the response status should be 400
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/attributes-groups/bdd-dup-grp/"
    Then the response status should be 200

  Scenario: Retrieve non-existent attributes group returns 404
    When I GET the v2 admin endpoint "pim/admin/attributes-groups/does-not-exist-xyz/"
    Then the response status should be 404
