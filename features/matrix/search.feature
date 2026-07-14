@matrix @import-verification @search
Feature: Matrix Product Search
  Verify that the Matrix search functionality works across product names,
  SKUs, and searchable features (material_composition).

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  Scenario: Search by product name returns results
    When I GET the Matrix endpoint "products/" with params
      | param    | value  |
      | search   | Orion  |
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Search by SKU returns exact product
    When I GET the Matrix endpoint "products/" with params
      | param    | value    |
      | search   | ENT-S001 |
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Search by material returns results (searchable feature)
    When I GET the Matrix endpoint "products/" with params
      | param    | value   |
      | search   | ceramic |
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Search with no match returns empty
    When I GET the Matrix endpoint "products/" with params
      | param    | value                    |
      | search   | xyznonexistent12345zzz   |
    Then the response status should be 200
    And the response should contain 0 items
