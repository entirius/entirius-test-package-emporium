@pim-csv @import-verification
Feature: Attribute Import Verification
  As a platform operator
  I want to verify that product attributes were imported correctly
  So that I know badge, brand, series, and options are available

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  Scenario: Products have badge attributes from CSV
    Given the CSV attributes are loaded for type "badge"
    When I GET the Cynthia endpoint "products/"
    Then the response status should be 200
    And products with badges should reference valid badge values

  Scenario: Products have series attributes from CSV
    Given the CSV attributes are loaded for type "series"
    When I GET the Cynthia endpoint "products/"
    Then the response status should be 200
    And products with series should reference valid series values

  Scenario: Badge CSV is non-empty
    Given the CSV attributes are loaded for type "badge"
    Then the CSV attributes should be non-empty

  Scenario: Brand CSV is non-empty
    Given the CSV attributes are loaded for type "brand"
    Then the CSV attributes should be non-empty

  Scenario: Series CSV is non-empty
    Given the CSV attributes are loaded for type "series"
    Then the CSV attributes should be non-empty

  Scenario: Options CSV is non-empty
    Given the CSV attributes are loaded for type "options"
    Then the CSV attributes should be non-empty
