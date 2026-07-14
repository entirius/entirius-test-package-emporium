@matrix @import-verification @bundle-config
Feature: Bundle Config API
  As an API consumer
  I want to retrieve bundle configuration from the Matrix API
  So that I can display the bundle product selector in the storefront

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  Scenario: Bundle config endpoint returns data for bundle SKU
    When I GET the Matrix endpoint "bundle-config/" with params
      | param | value     |
      | sku[] | ENT-BND01 |
    Then the response status should be 200
    And the bundle config response should contain 1 bundle

  Scenario: Bundle config contains sub_items
    When I GET the Matrix endpoint "bundle-config/" with params
      | param | value     |
      | sku[] | ENT-BND01 |
    Then the response status should be 200
    And the bundle config for "ENT-BND01" should have 3 sub_items

  Scenario: Sub_items have extension fields with correct values
    When I GET the Matrix endpoint "bundle-config/" with params
      | param | value     |
      | sku[] | ENT-BND01 |
    Then the response status should be 200
    And the bundle config sub_item "ENT-S001" should have extension fields
      | field                | value |
      | is_required          | true  |
      | is_default           | true  |
      | can_change_quantity   | false |
    And the bundle config sub_item "ENT-C001" should have extension fields
      | field                | value |
      | is_required          | false |
      | is_default           | false |
      | can_change_quantity   | true  |

  Scenario: Bundle config has limit fields in response
    When I GET the Matrix endpoint "bundle-config/" with params
      | param | value     |
      | sku[] | ENT-BND01 |
    Then the response status should be 200
    And the bundle config for "ENT-BND01" should have the field "max_limit"
    And the bundle config for "ENT-BND01" should have the field "min_limit"

  Scenario: Sub_items include price data
    When I GET the Matrix endpoint "bundle-config/" with params
      | param | value     |
      | sku[] | ENT-BND01 |
    Then the response status should be 200
    And each bundle config sub_item should have a price object
