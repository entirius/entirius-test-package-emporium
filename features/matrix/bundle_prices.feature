@matrix @import-verification @bundle-prices
Feature: Bundle Prices API
  As an API consumer
  I want to retrieve bundle component prices from the Matrix API
  So that I can display bundle pricing with sub-items

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  Scenario: Bundle price endpoint returns data for bundle SKU
    When I GET the Matrix endpoint "prices-bundle/" with params
      | param | value    |
      | sku   | ENT-BND01 |
    Then the response status should be 200
    And the bundle price response should contain items

  Scenario: Bundle price response contains price fields
    When I GET the Matrix endpoint "prices-bundle/" with params
      | param | value    |
      | sku   | ENT-BND01 |
    Then the response status should be 200
    And each bundle price item should have the field "sku"
    And each bundle price item should have the field "price"

  Scenario: Second bundle SKU also returns price data
    When I GET the Matrix endpoint "prices-bundle/" with params
      | param | value    |
      | sku   | ENT-BND02 |
    Then the response status should be 200
    And the bundle price response should contain items

  Scenario: Bundle price returns component items
    When I GET the Matrix endpoint "prices-bundle/" with params
      | param | value    |
      | sku   | ENT-BND01 |
    Then the response status should be 200
    And the bundle price response should contain at least 3 items
