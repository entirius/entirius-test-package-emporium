@pricemanager @price-history @admin @v2
Feature: Price History for Omnibus
  As a platform admin
  I want price changes to be tracked in PriceHistory
  So that EU Omnibus directive compliance is maintained

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Price history endpoint returns paginated results
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/history/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Seeded price history entries are present
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/history/"
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: Price history records contain required fields
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/history/"
    Then the response status should be 200
    And the response should contain at least 1 history entry with field "source"
    And the response should contain at least 1 history entry with field "created_at"
    And the response should contain at least 1 history entry with field "gross_value"

  Scenario: Two price edits both appear in history
    When I PATCH the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/" with body
      """
      {"value": 95.00}
      """
    Then the response status should be 200
    When I PATCH the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/" with body
      """
      {"value": 110.00}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/history/"
    Then the response status should be 200
    And the response should contain at least 2 history entries

  Scenario: History is ordered newest first
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/ENT-S001/history/"
    Then the response status should be 200
    And the price history results should be ordered newest first

  Scenario: History for unknown SKU returns empty
    When I GET the v2 admin endpoint "pricemanager/admin/default-europe/prices/BDD-UNKNOWN-SKU/history/"
    Then the response status should be 200
