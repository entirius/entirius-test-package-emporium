@pim-csv @import-verification @product-types
Feature: Product Types Import Verification
  As a platform operator
  I want to verify that all product types are imported correctly
  So that I know the CSV importer handles simple, configurable, bundle, and custom products

  Background:
    Given the test package has been imported

  Scenario: CSV contains all expected product types
    Given the CSV product type counts are loaded for the primary channel
    Then the CSV should contain "simple" products
    And the CSV should contain "config" products
    And the CSV should contain "bundle" products
    And the CSV should contain "custom" products

  Scenario: CSV has correct count of simple products
    Given the CSV product type counts are loaded for the primary channel
    Then the CSV should contain 28 "simple" products

  Scenario: CSV has correct count of configurable products
    Given the CSV product type counts are loaded for the primary channel
    Then the CSV should contain 2 "config" products

  Scenario: CSV has correct count of bundle products
    Given the CSV product type counts are loaded for the primary channel
    Then the CSV should contain 2 "bundle" products

  Scenario: CSV has correct count of custom products
    Given the CSV product type counts are loaded for the primary channel
    Then the CSV should contain 1 "custom" products

  Scenario: Total product count matches expected
    Given the CSV product type counts are loaded for the primary channel
    Then the total CSV product count should be 33

  Scenario: All configurable products exist in API
    Given the channel is the primary channel
    And the CSV products of type "config" are loaded for the primary channel
    When I GET the Cynthia endpoint "products/"
    Then the response status should be 200
    And every CSV product SKU should exist in the API response

  Scenario: All bundle products exist in API
    Given the channel is the primary channel
    And the CSV products of type "bundle" are loaded for the primary channel
    When I GET the Cynthia endpoint "products/"
    Then the response status should be 200
    And every CSV product SKU should exist in the API response

  Scenario: All custom products exist in API
    Given the channel is the primary channel
    And the CSV products of type "custom" are loaded for the primary channel
    When I GET the Cynthia endpoint "products/"
    Then the response status should be 200
    And every CSV product SKU should exist in the API response
