@matrix @import-verification @attributes
Feature: Matrix Product Attributes
  Verify that VisibilityFeatures configuration controls which attributes
  are returned when fetch_attributes=true on the products endpoint.

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  Scenario: Products with fetch_attributes return attribute list
    When I GET the Matrix endpoint "products/" with params
      | param            | value |
      | fetch_attributes | true  |
      | limit            | 5     |
    Then the response status should be 200
    And each product should have an "attributes" field

  Scenario: Visible attributes include configured features
    When I GET the Matrix endpoint "products/" with params
      | param            | value |
      | fetch_attributes | true  |
      | limit            | 5     |
    Then the response status should be 200
    And product attributes should include feature "series"

  Scenario: Boolean attribute has correct value type
    When I GET the Matrix endpoint "products/" with params
      | param            | value |
      | fetch_attributes | true  |
      | limit            | 5     |
    Then the response status should be 200
    And product attributes for "is_handcrafted" should have boolean-like values

  Scenario: Decimal attribute has numeric value
    When I GET the Matrix endpoint "products/" with params
      | param            | value |
      | fetch_attributes | true  |
      | limit            | 5     |
    Then the response status should be 200
    And product attributes for "weight_kg" should have numeric values
