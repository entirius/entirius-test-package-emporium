@admin @pricemanager-admin @v2
Feature: PriceManager Admin API v2
  As a platform admin
  I want to manage prices, channels, tax classes, and currencies
  So that products have correct per-country pricing

  Background:
    Given the test package has been imported

  # --- Authentication ---

  Scenario: Unauthenticated request returns 401
    When I GET the v2 admin endpoint "pricemanager/admin/channels/" without auth
    Then the response status should be 401

  Scenario: Non-admin user returns 403
    And I am authenticated as a regular user
    When I GET the v2 admin endpoint "pricemanager/admin/channels/"
    Then the response status should be 403

  Scenario: Unauthenticated request returns structured error
    When I GET the v2 admin endpoint "pricemanager/admin/channels/" without auth
    Then the response status should be 401
    And the error response should have error code "AUTHENTICATION_REQUIRED"
    And the error response should have a debug_id

  # --- Channels ---

  Scenario: Admin can list channels
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/channels/"
    Then the response status should be 200

  Scenario: Channels list contains seeded entries
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/channels/"
    Then the response status should be 200
    And the results should contain an item with "idx" equal to "default-europe"
    And the results should contain an item with "idx" equal to "default-local"

  Scenario: Admin can view channel detail
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/channels/default-europe/"
    Then the response status should be 200
    And the response should have the fields
      | field               |
      | idx                 |
      | name                |
      | calculate_direction |

  Scenario: Non-existent channel returns 404
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/channels/does-not-exist/"
    Then the response status should be 404

  Scenario: Admin can sync channels from PIM
    Given I am authenticated as an admin user
    When I POST to the v2 admin endpoint "pricemanager/admin/channels/sync/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response should have the fields
      | field  |
      | synced |

  # --- Tax Classes ---

  Scenario: Admin can list tax classes
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/tax-classes/"
    Then the response status should be 200
    And the results should contain an item with "idx" equal to "standard-rate"

  Scenario: Admin can view tax class with rates
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/tax-classes/standard-rate/"
    Then the response status should be 200
    And the response field "idx" should equal "standard-rate"
    And the response field "rates" should be a list

  Scenario: Tax class rates include seeded countries
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/tax-classes/standard-rate/"
    Then the response status should be 200
    And the response field "rates" should be a list

  Scenario: Non-existent tax class returns 404
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/tax-classes/no-such-class/"
    Then the response status should be 404

  # --- Currencies ---
  # Currencies moved to django-regional in 1.7.0 (see admin/regional_admin.feature).

  # --- Prices (channel-scoped) ---

  Scenario: Admin can list prices for a channel
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Prices list contains seeded SKUs
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/" with params
      | param     | value   |
      | page_size | 100     |
    Then the response status should be 200
    And the results should contain an item with "sku" equal to "ENT-S001"

  Scenario: Admin can view price detail for a SKU
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/"
    Then the response status should be 200
    And the response should have the fields
      | field  |
      | sku    |
      | prices |

  Scenario: Price detail for unknown SKU returns 404
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/NO-SUCH-SKU/"
    Then the response status should be 404

  Scenario: Admin can edit a product price
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/" with body
      """
      {"value": 99.00}
      """
    Then the response status should be 200
    And the response field "changes_logged" should not be null

  Scenario: Price edit with invalid payload returns 400
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/" with body
      """
      {"value": "not-a-number"}
      """
    Then the response status should be 400

  # --- Price History ---

  Scenario: Admin can view price history for a SKU
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/history/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Price history contains seeded entries
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/history/"
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: History for unknown SKU returns empty
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/NO-SUCH-SKU/history/"
    Then the response status should be 200
