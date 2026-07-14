@admin @pim-admin @v2
Feature: PIM Admin API v2
  As an admin user
  I want to manage products and categories via the admin API
  So that I can maintain the product catalog

  Background:
    Given the test package has been imported

  # --- Authentication ---

  Scenario: Unauthenticated request returns 401
    Given the channel is the primary channel
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/" without auth
    Then the response status should be 401

  Scenario: Non-admin user returns 403
    Given the channel is the primary channel
    And I am authenticated as a regular user
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/"
    Then the response status should be 403

  Scenario: Admin user can access the API
    Given the channel is the primary channel
    And I am authenticated as an admin user
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/"
    Then the response status should be 200

  # --- Products ---

  Scenario: Products list returns paginated structure
    Given the channel is the primary channel
    And I am authenticated as an admin user
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Products list respects page_size parameter
    Given the channel is the primary channel
    And I am authenticated as an admin user
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/" with params
      | param     | value |
      | page_size | 5     |
    Then the response status should be 200
    And the results should contain at most 5 items

  Scenario: Products list caps at max page_size
    Given the channel is the primary channel
    And I am authenticated as an admin user
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/" with params
      | param     | value |
      | page_size | 500   |
    Then the response status should be 200
    And the results should contain at most 100 items

  Scenario: Product detail returns expected fields
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the CSV products are loaded for the primary channel
    When I GET the v2 admin endpoint for the first CSV product
    Then the response status should be 200
    And the response should have the fields
      | field  |
      | sku    |
      | name   |

  # --- Categories ---

  Scenario: Categories list returns paginated structure
    Given the channel is the primary channel
    And I am authenticated as an admin user
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/categories/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  # --- Error Response Structure ---

  Scenario: Unauthenticated request returns structured error
    Given the channel is the primary channel
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/" without auth
    Then the response status should be 401
    And the error response should have error code "AUTHENTICATION_REQUIRED"
    And the error response should have a debug_id

  Scenario: Non-admin user returns structured error
    Given the channel is the primary channel
    And I am authenticated as a regular user
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/"
    Then the response status should be 403
    And the error response should have error code "PERMISSION_DENIED"
    And the error response should have a debug_id
