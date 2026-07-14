@matrix @import-verification @configurable
Feature: Configurable Products API
  As an API consumer
  I want to verify configurable products in the Matrix API
  So that I can display product variants in the storefront

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  Scenario: Configurable products appear in Matrix with correct type
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And the products with type "CONFIGURABLE" should include
      | sku       |
      | ENT-CFG01 |
      | ENT-CFG02 |

  Scenario: Configurable product variants endpoint returns options
    When I GET the Matrix detail "products/captains-living-room-set/variants/"
    Then the response status should be 200
    And the variants response should have options
    And the variants options should include feature "series"

  Scenario: Variants endpoint returns child products
    When I GET the Matrix detail "products/captains-living-room-set/variants/"
    Then the response status should be 200
    And the variants products should include SKUs
      | sku      |
      | ENT-S001 |
      | ENT-S002 |
      | ENT-C001 |

  Scenario: Variant products have configurable feature attributes
    When I GET the Matrix detail "products/captains-living-room-set/variants/"
    Then the response status should be 200
    And each variant product should have attributes for feature "series"

  Scenario: Second configurable product has variants
    When I GET the Matrix detail "products/stationmasters-office-set/variants/"
    Then the response status should be 200
    And the variants products should include SKUs
      | sku      |
      | ENT-C005 |
      | ENT-D001 |
