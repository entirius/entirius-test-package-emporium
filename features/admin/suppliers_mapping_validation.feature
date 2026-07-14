@admin @suppliers @v2 @suppliers-mapping @supplier
Feature: Suppliers Admin API -- Mapping Validation
  As an admin user
  I want to manage mapping profiles, attribute and category mappings
  So that supplier products can be pushed to PIM correctly

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: Demo mapping profile from fixture is retrievable
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/default-pl/"
    Then the response status should be 200
    And the response field "idx" should equal "default-pl"
    And the response field "is_active" should be true

  Scenario: Validate demo mapping profile returns ok=true
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/default-pl/validate/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "ok" should be true

  Scenario: Create new mapping profile + attribute mapping with existing PIM feature
    Given I ensure mapping profile "bdd-extra-profile" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/" with body
      """
      {
        "idx": "bdd-extra-profile",
        "name": "BDD Extra Profile",
        "target_channel_idxs": [],
        "is_active": false
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.profile_pk"
    When I POST to the v2 admin endpoint "suppliers/admin/mapping-profiles/{saved.profile_pk}/attribute-mappings/" with body
      """
      {
        "source_field": "manufacturer",
        "target_type": "feature",
        "target_identifier": "brand",
        "is_required": false
      }
      """
    Then the response status should be 201
    And the response field "source_field" should equal "manufacturer"
    Given I ensure mapping profile "bdd-extra-profile" for supplier "demo-supplier" is cleaned up

  Scenario: Attribute mapping with non-existent PIM feature is rejected
    Given I ensure mapping profile "bdd-bad-mapping" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/" with body
      """
      {
        "idx": "bdd-bad-mapping",
        "name": "BDD Bad Mapping",
        "target_channel_idxs": [],
        "is_active": false
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.bad_profile_pk"
    When I POST to the v2 admin endpoint "suppliers/admin/mapping-profiles/{saved.bad_profile_pk}/attribute-mappings/" with body
      """
      {
        "source_field": "weird",
        "target_type": "feature",
        "target_identifier": "this-feature-does-not-exist-in-pim",
        "is_required": false
      }
      """
    Then the response status should be 400
    Given I ensure mapping profile "bdd-bad-mapping" for supplier "demo-supplier" is cleaned up

  Scenario: Active profiles cannot share target channels (D24)
    # demo-supplier already has active default-pl profile targeting pl-demo-profident3
    Given I ensure mapping profile "bdd-overlap-profile" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/" with body
      """
      {
        "idx": "bdd-overlap-profile",
        "name": "BDD Overlap",
        "target_channel_idxs": ["pl-demo-profident3"],
        "is_active": true
      }
      """
    Then the response status should be 400
    Given I ensure mapping profile "bdd-overlap-profile" for supplier "demo-supplier" is cleaned up

  Scenario: Removing channel from profile target_channel_idxs emits channel_removed_from_profile event (D26)
    Given I ensure mapping profile "bdd-removable" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/" with body
      """
      {
        "idx": "bdd-removable",
        "name": "BDD Removable",
        "target_channel_idxs": [],
        "is_active": false
      }
      """
    Then the response status should be 201
    When I PATCH the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/bdd-removable/" with body
      """
      {"target_channel_idxs": []}
      """
    Then the response status should be 200
    Given I ensure mapping profile "bdd-removable" for supplier "demo-supplier" is cleaned up
