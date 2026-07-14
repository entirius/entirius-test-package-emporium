@admin @suppliers @v2 @suppliers-manual @supplier
Feature: Suppliers Admin API -- Manual ProductSupplierLink
  As an admin user
  I want to manually attach suppliers to existing PIM products via ProductSupplierLink
  So that I can model multi-supplier sourcing and operator-curated preferred supplier

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user
    And regional language "pl" id is stored as "lang_id"
    And regional currency "PLN" id is stored as "curr_id"

  Scenario: Create ProductSupplierLink for existing PIM SKU (real_product exists)
    # SKU "0001-0007" exists in import-package PIM data (Profident demo)
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/product-links/" with body
      """
      {
        "real_product_sku": "0001-0007",
        "supplier_idx": "demo-supplier",
        "external_id": "DEMO-LINK-7",
        "priority": 0,
        "is_preferred": false,
        "is_active": true,
        "notes": "BDD manual link"
      }
      """
    Then the response status should be 201
    And the response field "real_product_sku" should equal "0001-0007"
    And the response field "is_preferred" should be false
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up

  Scenario: Create link for non-existent SKU returns 400
    Given I ensure product supplier link for sku "BDD-NONEXIST-SKU" supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/product-links/" with body
      """
      {
        "real_product_sku": "BDD-NONEXIST-SKU",
        "supplier_idx": "demo-supplier",
        "external_id": "",
        "priority": 0,
        "is_preferred": false,
        "is_active": true,
        "notes": ""
      }
      """
    Then the response status should be 400

  Scenario: Set preferred unsets sibling preferred at the same SKU (D25)
    # Create a supplier so we have 2 distinct suppliers per SKU
    Given I ensure supplier with idx "bdd-second-sup" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "bdd-second-sup",
        "name": "BDD Second Supplier",
        "supplier_role": "trade",
        "supplier_type": "feed",
        "review_mode": "manual",
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id},
        "sku_prefix": "BDDS"
      }
      """
    Then the response status should be 201
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up
    Given I ensure product supplier link for sku "0001-0007" supplier "bdd-second-sup" is cleaned up
    # First link: demo-supplier preferred=true
    When I POST to the v2 admin endpoint "suppliers/admin/product-links/" with body
      """
      {
        "real_product_sku": "0001-0007",
        "supplier_idx": "demo-supplier",
        "external_id": "DEMO-001",
        "priority": 0,
        "is_preferred": true,
        "is_active": true,
        "notes": ""
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.first_link_pk"
    # Second link: bdd-second-sup preferred=false initially
    When I POST to the v2 admin endpoint "suppliers/admin/product-links/" with body
      """
      {
        "real_product_sku": "0001-0007",
        "supplier_idx": "bdd-second-sup",
        "external_id": "BDDS-001",
        "priority": 0,
        "is_preferred": false,
        "is_active": true,
        "notes": ""
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.second_link_pk"
    # Now set second as preferred -> first should auto-unset
    When I POST to the v2 admin endpoint "suppliers/admin/product-links/{saved.second_link_pk}/set-preferred/" with body
      """
      {}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/product-links/{saved.first_link_pk}/"
    Then the response status should be 200
    And the response field "is_preferred" should be false
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up
    Given I ensure product supplier link for sku "0001-0007" supplier "bdd-second-sup" is cleaned up
    Given I ensure supplier with idx "bdd-second-sup" is cleaned up

  Scenario: Unset preferred via PATCH is_preferred=false (Stage 7 workaround)
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/product-links/" with body
      """
      {
        "real_product_sku": "0001-0007",
        "supplier_idx": "demo-supplier",
        "external_id": "DEMO-007",
        "priority": 0,
        "is_preferred": true,
        "is_active": true,
        "notes": ""
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.unset_pk"
    When I PATCH the v2 admin endpoint "suppliers/admin/product-links/{saved.unset_pk}/" with body
      """
      {"is_preferred": false}
      """
    Then the response status should be 200
    And the response field "is_preferred" should be false
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up

  Scenario: PATCH cannot mutate immutable real_product_sku (D15)
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/product-links/" with body
      """
      {
        "real_product_sku": "0001-0007",
        "supplier_idx": "demo-supplier",
        "external_id": "DEMO-IMM",
        "priority": 0,
        "is_preferred": false,
        "is_active": true,
        "notes": ""
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.imm_pk"
    When I PATCH the v2 admin endpoint "suppliers/admin/product-links/{saved.imm_pk}/" with body
      """
      {"real_product_sku": "0001-0008"}
      """
    Then the response status should be 400
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up

  Scenario: Update notes / priority works (mutable operator fields)
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/product-links/" with body
      """
      {
        "real_product_sku": "0001-0007",
        "supplier_idx": "demo-supplier",
        "external_id": "DEMO-MUT",
        "priority": 0,
        "is_preferred": false,
        "is_active": true,
        "notes": ""
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.mut_pk"
    When I PATCH the v2 admin endpoint "suppliers/admin/product-links/{saved.mut_pk}/" with body
      """
      {"notes": "BDD updated notes", "priority": 5}
      """
    Then the response status should be 200
    And the response field "notes" should equal "BDD updated notes"
    And the response field "priority" should equal integer 5
    Given I ensure product supplier link for sku "0001-0007" supplier "demo-supplier" is cleaned up
