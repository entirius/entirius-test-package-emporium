@matrix @import-verification
Feature: Matrix Read Model API
  As an API consumer
  I want to retrieve product data from the Matrix read model
  So that I can display enriched product data with prices and stock

  Background:
    Given the test package has been imported

  Scenario: List products from matrix for primary channel
    Given the channel is the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And the response should be a non-empty list

  Scenario: Matrix products have enriched fields
    Given the channel is the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And each item should have the fields
      | field       |
      | sku         |
      | name        |
      | final_price |
      | on_stock    |

  Scenario: Matrix contains all imported products
    Given the channel is the primary channel
    When I GET the Matrix endpoint "products/" with params
      | param     | value |
      | page_size | 100   |
    Then the response status should be 200
    And the response count should be at least the CSV product count

  Scenario: Matrix products have brand information
    Given the channel is the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And each item should have the field "brands"
