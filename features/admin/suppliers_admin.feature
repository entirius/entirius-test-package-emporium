@admin @suppliers @v2 @crud @suppliers-crud @supplier
Feature: Suppliers Admin API -- Supplier CRUD
  As an admin user
  I want to create, read, update, and soft/hard-delete suppliers
  So that I can manage the supplier registry

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user
    And regional language "pl" id is stored as "lang_id"
    And regional currency "PLN" id is stored as "curr_id"

  # --- Fixture present ---

  Scenario: Demo supplier from fixture is retrievable
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/"
    Then the response status should be 200
    And the response field "idx" should equal "demo-supplier"
    And the response field "name" should equal "Demo Supplier"
    And the response field "supplier_role" should equal "trade"
    And the response field "supplier_type" should equal "feed"
    And the response field "review_mode" should equal "manual"
    And the response field "is_active" should be true
    And the response field "sku_prefix" should equal "DMS"

  Scenario: Suppliers list contains demo-supplier from fixture
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/"
    Then the response status should be 200
    And the results should contain an item with "idx" equal to "demo-supplier"

  # --- Auth ---

  Scenario: Anonymous request to suppliers list returns 401
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/" without auth
    Then the response status should be 401

  Scenario: Regular user request to suppliers list returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/"
    Then the response status should be 403

  # --- Create ---

  Scenario: Create supplier with valid data
    Given I ensure supplier with idx "bdd-supplier-create" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "bdd-supplier-create",
        "name": "BDD Created Supplier",
        "supplier_role": "trade",
        "supplier_type": "feed",
        "review_mode": "manual",
        "is_active": true,
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id},
        "sku_prefix": "BDDC",
        "qty_subtract": 0,
        "qty_minimum": 0
      }
      """
    Then the response status should be 201
    And the response field "idx" should equal "bdd-supplier-create"
    And the response field "name" should equal "BDD Created Supplier"
    Given I ensure supplier with idx "bdd-supplier-create" is cleaned up

  Scenario: Create supplier with duplicate idx returns 400
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "demo-supplier",
        "name": "Duplicate",
        "supplier_role": "trade",
        "supplier_type": "feed",
        "review_mode": "manual",
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id}
      }
      """
    Then the response status should be 400

  Scenario: Create supplier with non-trade role rejected (NotImplementedError per D19)
    Given I ensure supplier with idx "bdd-data-role" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "bdd-data-role",
        "name": "Data Role Supplier",
        "supplier_role": "data",
        "supplier_type": "feed",
        "review_mode": "manual",
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id}
      }
      """
    Then the response status should be 400

  # --- Update ---

  Scenario: Partial update supplier sets new contact email
    Given I ensure supplier with idx "bdd-supplier-upd" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "bdd-supplier-upd",
        "name": "BDD Update Supplier",
        "supplier_role": "trade",
        "supplier_type": "feed",
        "review_mode": "manual",
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id},
        "sku_prefix": "BDDU"
      }
      """
    Then the response status should be 201
    When I PATCH the v2 admin endpoint "suppliers/admin/suppliers/bdd-supplier-upd/" with body
      """
      {"contact_email": "ops@bdd-supplier.example", "lead_time_days": 14}
      """
    Then the response status should be 200
    And the response field "contact_email" should equal "ops@bdd-supplier.example"
    And the response field "lead_time_days" should equal integer 14
    Given I ensure supplier with idx "bdd-supplier-upd" is cleaned up

  # --- Delete (soft + hard + impact) ---

  Scenario: Soft delete supplier sets is_active=false (idempotent)
    Given I ensure supplier with idx "bdd-supplier-soft" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "bdd-supplier-soft",
        "name": "BDD Soft Delete Supplier",
        "supplier_role": "trade",
        "supplier_type": "feed",
        "review_mode": "manual",
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id}
      }
      """
    Then the response status should be 201
    When I DELETE the v2 admin endpoint "suppliers/admin/suppliers/bdd-supplier-soft/"
    Then the response status should be 200
    And the response field "mode" should equal "soft"
    # Idempotent re-soft-delete
    When I DELETE the v2 admin endpoint "suppliers/admin/suppliers/bdd-supplier-soft/"
    Then the response status should be 200
    And the response field "mode" should equal "soft"
    Given I ensure supplier with idx "bdd-supplier-soft" is cleaned up

  Scenario: Soft-deleted supplier is invisible in default list (is_active filter)
    Given I ensure supplier with idx "bdd-supplier-hidden" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "bdd-supplier-hidden",
        "name": "BDD Hidden",
        "supplier_role": "trade",
        "supplier_type": "feed",
        "review_mode": "manual",
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id}
      }
      """
    Then the response status should be 201
    When I DELETE the v2 admin endpoint "suppliers/admin/suppliers/bdd-supplier-hidden/"
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/?is_active=true"
    Then the response status should be 200
    And the results should not contain an item with "idx" equal to "bdd-supplier-hidden"
    Given I ensure supplier with idx "bdd-supplier-hidden" is cleaned up

  Scenario: GET delete-impact returns counts without deleting (D37)
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/delete-impact/"
    Then the response status should be 200
    And the response field "supplier_idx" should equal "demo-supplier"
    And the response field "affected_links_count" should equal integer 0
    # Confirm supplier still exists
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/"
    Then the response status should be 200

  Scenario: Hard delete with force=true cascades and emits supplier_deleted event (D37)
    Given I ensure supplier with idx "bdd-supplier-hard" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "bdd-supplier-hard",
        "name": "BDD Hard Delete",
        "supplier_role": "trade",
        "supplier_type": "feed",
        "review_mode": "manual",
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id}
      }
      """
    Then the response status should be 201
    When I DELETE the v2 admin endpoint "suppliers/admin/suppliers/bdd-supplier-hard/?force=true"
    Then the response status should be 200
    And the response field "mode" should equal "hard"
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/bdd-supplier-hard/"
    Then the response status should be 404
    When I GET the v2 admin endpoint "suppliers/admin/events/?event_type=supplier_deleted&page_size=20"
    Then the response status should be 200
    And the events list should contain at least one event of type "supplier_deleted"

  Scenario: List filter by supplier_role returns only matching
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/?supplier_role=trade"
    Then the response status should be 200
    And the results should contain an item with "idx" equal to "demo-supplier"
