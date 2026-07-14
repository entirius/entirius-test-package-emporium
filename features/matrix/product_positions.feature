@matrix @import-verification @product-positions
Feature: Product Positions API
  As an API consumer
  I want to verify products are returned in the correct position order
  So that the storefront displays products in the intended sequence

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And the CSV product positions are loaded for the primary channel

  Scenario: Products in "sofas" category are ordered by position
    When I GET the Matrix endpoint "products/" with params
      | param            | value |
      | category_url_key | sofas |
    Then the response status should be 200
    And the response SKU order should match CSV positions for category "sofas"

  Scenario: Products in "chairs" category are ordered by position
    When I GET the Matrix endpoint "products/" with params
      | param            | value  |
      | category_url_key | chairs |
    Then the response status should be 200
    And the response SKU order should match CSV positions for category "chairs"

  Scenario: Products in "sale" category are ordered by position
    When I GET the Matrix endpoint "products/" with params
      | param            | value |
      | category_url_key | sale  |
    Then the response status should be 200
    And the response SKU order should match CSV positions for category "sale"

  Scenario: Products in "bedroom" category are ordered by position
    When I GET the Matrix endpoint "products/" with params
      | param            | value   |
      | category_url_key | bedroom |
    Then the response status should be 200
    And the response SKU order should match CSV positions for category "bedroom"
