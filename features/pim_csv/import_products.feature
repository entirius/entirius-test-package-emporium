@pim-csv @import-verification
Feature: Product Import Verification
  As a platform operator
  I want to verify that CSV-imported products match the API
  So that I know the product import pipeline works correctly

  Background:
    Given the test package has been imported

  Scenario: All CSV products exist in primary channel API
    Given the channel is the primary channel
    And the CSV products are loaded for the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And every CSV product SKU should exist in the API response

  Scenario: All CSV products exist in all configured channels
    Given for each configured channel the CSV products are verified against the API

  Scenario: Product count matches CSV for primary channel
    Given the channel is the primary channel
    And the CSV products are loaded for the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And the API product count should be at least the CSV count

  Scenario: Product names match CSV data
    Given the channel is the primary channel
    And the CSV products are loaded for the primary channel
    When I GET the Matrix endpoint "products/"
    Then the response status should be 200
    And each CSV product name should match the API response
