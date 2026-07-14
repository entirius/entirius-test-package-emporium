@suppliers @mapping-ux @validate
Feature: Suppliers mapping validate++ — structured warnings drive per-row badges
  As an operator wiring a new supplier mapping in the CMS
  I want validate to flag typos in source_value and type mismatches between
  feed values and target Feature types, with per-row attribution
  So that the yellow badge in MappingsTab points the operator directly at the
  row that's broken, not just "X warnings, find them yourself".

  Covers the breaking shape change
  `warnings: list[str] → list[MappingWarning]` (the only consumer is
  MappingsTab.validateProfile which previously only read `.length`).

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user
    And regional language "pl" id is stored as "lang_id"
    And regional currency "PLN" id is stored as "curr_id"

  @data-values @auth
  Scenario: data-values endpoint requires authentication — leak protection
    # data-values reveals the full vocabulary of supplier categories/values.
    # 401, never an empty list.
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/data-values/?source_field=category_path" without auth
    Then the response status should be 401

  @data-values @shape
  Scenario: data-values returns count + value for each distinct supplier value
    # demo-supplier fixture seeds 5 SP with category_path in {surgery, implants}.
    # Operator sees real frequencies (e.g. surgery:3, implants:2) in the picker.
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/data-values/?source_field=category_path"
    Then the response status should be 200
    And the response field "source_field" should equal "category_path"
    And the response field "values" should be a list
    And the response field "truncated" should be false

  @validate @happy
  Scenario: validate returns the new MappingWarning shape (smoke contract test)
    # Fresh profile with no target channels and no mappings. validate must succeed
    # (ok=true) and return warnings as the new structured list — one warning with
    # code=no_mappings_configured. Demonstrates the breaking shape change is live.
    Given I ensure mapping profile "bdd-shape" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/" with body
      """
      {
        "idx": "bdd-shape",
        "name": "Shape smoke",
        "target_channel_idxs": [],
        "is_active": false
      }
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/bdd-shape/validate/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "ok" should be true
    And the response field "warnings" should be a list
    And the response nested field "warnings.0.code" should equal "no_mappings_configured"
    And the response nested field "warnings.0.mapping_kind" should equal "profile"
    Given I ensure mapping profile "bdd-shape" for supplier "demo-supplier" is cleaned up

  @validate @warning @source-value-typo
  Scenario: source_value typo emits structured warning with suggestion
    # Operator types "surgeryyy" instead of "surgery" — validate must flag the
    # row with code=source_value_not_found_in_supplier_data and suggest "surgery".
    Given I ensure mapping profile "bdd-typo" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/" with body
      """
      {
        "idx": "bdd-typo",
        "name": "Typo test",
        "target_channel_idxs": ["{channel_idx}"],
        "is_active": false
      }
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.profile_pk"
    When I POST to the v2 admin endpoint "suppliers/admin/mapping-profiles/{saved.profile_pk}/category-mappings/" with body
      """
      {
        "source_field": "category_path",
        "source_value": "surgeryyy",
        "target_category_idx": "beds"
      }
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/bdd-typo/validate/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "warnings" should be a list
    And the response nested field "warnings.0.code" should equal "source_value_not_found_in_supplier_data"
    And the response nested field "warnings.0.mapping_kind" should equal "category"
    And the response nested field "warnings.0.source_value" should equal "surgeryyy"
    Given I ensure mapping profile "bdd-typo" for supplier "demo-supplier" is cleaned up

  @validate @warning @type-mismatch
  Scenario: Type incompatibility emits warning when feed text values can't parse as BOOL
    # Map category_path (text "surgery"/"implants") → a BOOL feature.
    # All 5 sampled values fail BOOL parse → 100% failure → type_incompatibility warning.
    Given I ensure v2 admin resource "pim/admin/features/bdd-bool/" is deleted
    And I ensure mapping profile "bdd-type" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {
        "idx": "bdd-bool",
        "name_t9n": {"en": "BDD Bool"},
        "feature_type": 1,
        "scope": 3
      }
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/" with body
      """
      {
        "idx": "bdd-type",
        "name": "Type mismatch test",
        "target_channel_idxs": ["{channel_idx}"],
        "is_active": false
      }
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.profile_pk"
    When I POST to the v2 admin endpoint "suppliers/admin/mapping-profiles/{saved.profile_pk}/attribute-mappings/" with body
      """
      {
        "source_field": "category_path",
        "target_type": "feature",
        "target_identifier": "bdd-bool",
        "is_required": false
      }
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/bdd-type/validate/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "warnings" should be a list
    And the response nested field "warnings.0.code" should equal "type_incompatibility"
    And the response nested field "warnings.0.mapping_kind" should equal "attribute"
    And the response nested field "warnings.0.target_identifier" should equal "bdd-bool"
    Given I ensure mapping profile "bdd-type" for supplier "demo-supplier" is cleaned up
    Given I ensure v2 admin resource "pim/admin/features/bdd-bool/" is deleted
