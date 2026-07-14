@admin @regional @v2
Feature: Regional Admin API
  As an admin user
  I want to list languages, currencies, and countries
  So that downstream panels (suppliers, PIM, checkout) can resolve user-facing labels

  Background:
    Given the test package has been imported

  # --- Auth gates ---

  Scenario: Unauthenticated request returns 401 (languages)
    When I GET the v2 admin endpoint "regional/admin/languages/" without auth
    Then the response status should be 401

  Scenario: Unauthenticated request returns 401 (currencies)
    When I GET the v2 admin endpoint "regional/admin/currencies/" without auth
    Then the response status should be 401

  Scenario: Unauthenticated request returns 401 (countries)
    When I GET the v2 admin endpoint "regional/admin/countries/" without auth
    Then the response status should be 401

  # --- List endpoints ---

  Scenario: Admin can list languages
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "regional/admin/languages/"
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: Admin can list currencies
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "regional/admin/currencies/"
    Then the response status should be 200
    And the results should contain an item with "iso3" equal to "EUR"
    And the results should contain an item with "iso3" equal to "PLN"

  Scenario: Admin can list countries
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "regional/admin/countries/"
    Then the response status should be 200
    And the results should contain an item with "iso2" equal to "PL"
