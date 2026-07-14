@qms @import-verification
Feature: Quantity / Stock Verification
  As a platform operator
  I want to verify that CSV-imported quantities match the API
  So that I know stock levels are correct

  Background:
    Given the test package has been imported

  Scenario: Stock data exists for products
    Given the channel is the primary channel
    And the CSV quantities are loaded
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And the response should be a non-empty list

  Scenario: CSV quantities count matches product count
    Given the CSV quantities are loaded
    Then the CSV quantities count should match the CSV product count

  Scenario: Some products are out of stock
    Given the CSV quantities are loaded
    Then the CSV should have products with zero quantity

  Scenario: Some products are in stock
    Given the CSV quantities are loaded
    Then the CSV should have products with positive quantity

  Scenario: All zero-quantity SKUs from CSV are confirmed
    Given the CSV quantities are loaded
    Then all zero-quantity SKUs from CSV should be confirmed
