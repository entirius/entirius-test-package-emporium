@atlas @v2 @crud @sources
Feature: Atlas Admin API -- Source CRUD
  Sources are the full registry (kind = procurement / monitoring / enrichment);
  the supplier/competitor facades are kind-forced projections of the same rows.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user
    And regional language "en" id is stored as "lang_id"
    And regional currency "EUR" id is stored as "curr_id"
    And I ensure v2 admin resource "atlas/admin/sources/bdd-atlas-src/" is deleted

  Scenario: Create, retrieve and delete a source by idx
    When I POST to the v2 admin endpoint "atlas/admin/sources/" with body
      """
      {"idx": "bdd-atlas-src", "name": "BDD Atlas Source", "kind": "monitoring",
       "default_language_id": {lang_id}, "default_currency_id": {curr_id}}
      """
    Then the response status should be 201
    And the response field "idx" should equal "bdd-atlas-src"
    And the response field "kind" should equal "monitoring"
    When I GET the v2 admin endpoint "atlas/admin/sources/bdd-atlas-src/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "atlas/admin/sources/bdd-atlas-src/?force=true"
    Then the response status should be 200

  Scenario: Sources list filters by kind
    When I GET the v2 admin endpoint "atlas/admin/sources/" with params
      | param | value      |
      | kind  | monitoring |
    Then the response status should be 200
    And the results should contain an item with "idx" equal to "atl-watch-de"
    And the results should not contain an item with "idx" equal to "atl-nova"

  Scenario: Create rejects an unknown kind
    When I POST to the v2 admin endpoint "atlas/admin/sources/" with body
      """
      {"idx": "bdd-atlas-src", "name": "Bogus", "kind": "wholesale",
       "default_language_id": {lang_id}, "default_currency_id": {curr_id}}
      """
    Then the response status should be 400

  Scenario: Supplier facade projects only procurement sources
    When I GET the v2 admin endpoint "atlas/admin/suppliers/"
    Then the response status should be 200
    And the results should contain an item with "idx" equal to "atl-nova"
    And the results should not contain an item with "idx" equal to "atl-watch-de"

  Scenario: Competitor facade projects only monitoring sources
    When I GET the v2 admin endpoint "atlas/admin/competitors/"
    Then the response status should be 200
    And the results should contain an item with "idx" equal to "atl-watch-de"
    And the results should not contain an item with "idx" equal to "atl-nova"

  Scenario: Source endpoints refuse unauthenticated access
    When I GET the v2 admin endpoint "atlas/admin/sources/" without auth
    Then the response status should be 401
