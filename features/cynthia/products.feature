@cynthia @import-verification
Feature: Public Product API (via Matrix)
  As an API consumer
  I want to retrieve products from the Matrix API
  So that I can display product listings in the storefront

  Background:
    Given the test package has been imported

  Scenario: List all products for primary channel
    Given the channel is the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And the response count should match CSV product count

  Scenario: All CSV products exist in all configured channels
    Given for each configured channel the CSV products are verified against the API

  Scenario: Products have required fields
    Given the channel is the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And each item should have the fields
      | field       |
      | sku         |
      | name        |
      | url_key     |

  Scenario: First and last CSV products exist in API
    Given the channel is the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And the first CSV product SKU should exist in the API response
    And the last CSV product SKU should exist in the API response

  Scenario: Single product detail by url_key
    Given the channel is the primary channel
    Then the first CSV product detail should be accessible by url_key
