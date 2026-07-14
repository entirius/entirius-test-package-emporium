@pricemanager @import-verification
Feature: Price Verification
  As a platform operator
  I want to verify that CSV-imported prices match the API
  So that I know prices are correct in the storefront

  Background:
    Given the test package has been imported

  Scenario: Prices exist for primary channel products via matrix
    Given the channel is the primary channel
    And the CSV pricelist is loaded for the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And matrix products should have final_price values

  Scenario: CSV pricelist count matches product count
    Given the CSV pricelist is loaded for the primary channel
    Then the CSV pricelist count should match the CSV product count

  Scenario: Special prices exist for discounted products
    Given the CSV pricelist is loaded for the primary channel
    Then the CSV should have products with special prices
