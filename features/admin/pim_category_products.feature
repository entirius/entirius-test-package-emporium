@admin @pim-admin @v2 @category-products
Feature: PIM Admin API -- Product Positions in Category
  As an admin user
  I want to manage product positions within categories
  So that I can control the display order of products

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- Auth ---

  @auth
  Scenario: Unauthenticated request returns 401
    Given I clear auth token
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/"
    Then the response status should be 401

  @auth
  Scenario: Regular user returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/"
    Then the response status should be 403

  # --- List ---

  @list
  Scenario: List products in category returns positioned and unpositioned
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/"
    Then the response status should be 200
    And the response field "positioned" should be a list
    And the response field "unpositioned" should be a list
    And the response field "unpositioned_count" should not be null

  @list
  Scenario: Search products by SKU
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/?search=NONEXISTENT-SKU-XYZ"
    Then the response status should be 200
    And the response field "unpositioned_count" should equal integer 0

  @list
  Scenario: 404 for nonexistent category
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/nonexistent-bdd-cat/products/"
    Then the response status should be 404

  # --- Reorder ---

  @reorder
  Scenario: Pin a product by setting position > 0
    # First get a product SKU from the category
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/"
    Then the response status should be 200
    And the results list "unpositioned" should have at least 1 items
    Then I save the nested field "unpositioned.0.sku" as "saved.pin_sku"

    # Pin it
    When I PATCH the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/reorder/" with body
      """
      {"items": [{"sku": "{saved.pin_sku}", "position": 99}]}
      """
    Then the response status should be 200
    And the response field "reordered" should equal integer 1

    # Verify it appears in positioned
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/"
    Then the response status should be 200
    And the list "positioned" should contain an item with "sku" equal to "{saved.pin_sku}"

    # Unpin it (cleanup)
    When I PATCH the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/reorder/" with body
      """
      {"items": [{"sku": "{saved.pin_sku}", "position": 0}]}
      """
    Then the response status should be 200

  @reorder
  Scenario: Reorder auth — unauthenticated returns 401
    Given I clear auth token
    When I PATCH the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/reorder/" with body
      """
      {"items": []}
      """
    Then the response status should be 401

  @reorder
  Scenario: Reorder with invalid SKU returns 404
    When I PATCH the v2 admin endpoint "pim/admin/{channel_idx}/categories/sofas/products/reorder/" with body
      """
      {"items": [{"sku": "BDD-NONEXISTENT-SKU", "position": 1}]}
      """
    Then the response status should be 404
