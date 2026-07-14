@admin @pim-admin @v2 @crud @products
Feature: PIM Admin API -- Product CRUD
  As an admin user
  I want to create, read, update, and delete products
  So that I can manage the product catalog

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- List ---

  Scenario: Products list returns paginated structure
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |
    And the results count should be greater than 0

  Scenario: Products list supports search filter
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/" with params
      | param  | value |
      | search | sofa  |
    Then the response status should be 200
    And the response should have pagination fields
      | field   |
      | count   |
      | results |

  Scenario: Products list supports is_enabled filter
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/" with params
      | param      | value |
      | is_enabled | true  |
    Then the response status should be 200

  # --- Product Detail (existing product from import) ---

  Scenario: Product detail returns enriched fields
    And the CSV products are loaded for the primary channel
    When I GET the v2 admin endpoint for the first CSV product
    Then the response status should be 200
    And the response should have the fields
      | field              |
      | pk                 |
      | sku                |
      | name               |
      | name_t9n           |
      | visibility         |
      | visibility_name    |
      | is_enabled         |
      | product_class      |
      | product_class_name |
      | feature_set_idx    |
      | categories         |
      | attributes         |
    And the response field "name_t9n" should be a dict
    And the response field "categories" should be a list
    And the response field "attributes" should be a list

  # --- Full CRUD Lifecycle ---

  Scenario: Product CRUD lifecycle (create, retrieve, update, delete)
    # Cleanup
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/products/BDD-PROD-001/" is deleted
    # Create
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {
        "sku": "BDD-PROD-001",
        "feature_set_idx": "default",
        "visibility": 4,
        "is_enabled": true,
        "product_class": 1,
        "kind_of_product": 0,
        "weight": "2.50",
        "ean": "5901234567890"
      }
      """
    Then the response status should be 201
    And the response field "sku" should equal "BDD-PROD-001"
    And the response field "visibility" should equal integer 4
    And the response field "is_enabled" should be true
    And the response field "product_class" should equal integer 1
    And the response field "feature_set_idx" should equal "default"
    And the response field "weight" should not be null
    And the response field "ean" should not be null
    And the response field "categories" should be a list
    And the response field "attributes" should be a list
    # Retrieve
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-PROD-001/"
    Then the response status should be 200
    And the response field "sku" should equal "BDD-PROD-001"
    And the response field "pk" should not be null
    And the response field "name" should not be null
    And the response field "name_t9n" should be a dict
    # Update
    When I PATCH the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-PROD-001/" with body
      """
      {
        "visibility": 2,
        "is_enabled": false,
        "weight": "3.00"
      }
      """
    Then the response status should be 200
    And the response field "visibility" should equal integer 2
    And the response field "is_enabled" should be false
    And the response field "weight" should equal "3.00"
    # Verify update persisted
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-PROD-001/"
    Then the response status should be 200
    And the response field "visibility" should equal integer 2
    And the response field "is_enabled" should be false
    # Delete
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-PROD-001/"
    Then the response status should be 200
    # Verify deleted
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-PROD-001/"
    Then the response status should be 404

  # --- Product with Categories ---

  Scenario: Create product with category assignments
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/products/BDD-PROD-CAT/" is deleted
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/categories/bdd-prod-cat-1/" is deleted
    # Create a category first
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/categories/" with body
      """
      {"idx": "bdd-prod-cat-1", "name_t9n": {"en": "Prod Cat"}, "is_active": true, "is_in_menu": true}
      """
    Then the response status should be 201
    # Create product with category
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {
        "sku": "BDD-PROD-CAT",
        "feature_set_idx": "default",
        "visibility": 4,
        "is_enabled": true,
        "product_class": 1,
        "kind_of_product": 0,
        "category_idxs": ["bdd-prod-cat-1"]
      }
      """
    Then the response status should be 201
    And the response field "categories" should be a list
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-PROD-CAT/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/categories/bdd-prod-cat-1/"
    Then the response status should be 200

  # --- Bulk Update ---

  Scenario: Bulk update products changes is_enabled
    # Setup: create two products
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/products/BDD-BULK-A/" is deleted
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/products/BDD-BULK-B/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {"sku": "BDD-BULK-A", "feature_set_idx": "default", "visibility": 4, "is_enabled": true, "product_class": 1, "kind_of_product": 0}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {"sku": "BDD-BULK-B", "feature_set_idx": "default", "visibility": 4, "is_enabled": true, "product_class": 1, "kind_of_product": 0}
      """
    Then the response status should be 201
    # Bulk disable
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/bulk/" with body
      """
      {
        "skus": ["BDD-BULK-A", "BDD-BULK-B"],
        "is_enabled": false
      }
      """
    Then the response status should be 200
    # Verify both disabled
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-BULK-A/"
    Then the response status should be 200
    And the response field "is_enabled" should be false
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-BULK-B/"
    Then the response status should be 200
    And the response field "is_enabled" should be false
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-BULK-A/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-BULK-B/"
    Then the response status should be 200

  # --- Error Cases ---

  Scenario: Create product with duplicate SKU in same channel returns 400
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/products/BDD-DUP-SKU/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {"sku": "BDD-DUP-SKU", "feature_set_idx": "default", "visibility": 4, "is_enabled": true, "product_class": 1, "kind_of_product": 0}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {"sku": "BDD-DUP-SKU", "feature_set_idx": "default", "visibility": 4, "is_enabled": true, "product_class": 1, "kind_of_product": 0}
      """
    Then the response status should be 400
    # Cleanup
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-DUP-SKU/"
    Then the response status should be 200

  Scenario: Retrieve non-existent product returns 404
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/DOES-NOT-EXIST-XYZ/"
    Then the response status should be 404

  Scenario: Delete non-existent product returns 404
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/products/DOES-NOT-EXIST-XYZ/"
    Then the response status should be 404

  Scenario: Create product with invalid feature_set returns 404
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {"sku": "BDD-BAD-FS", "feature_set_idx": "nonexistent-fs", "visibility": 4, "is_enabled": true, "product_class": 1, "kind_of_product": 0}
      """
    Then the response status should be 404
