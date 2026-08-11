@atlas @v2 @seed-content
Feature: Atlas seed content contract
  The full seed (Step 3d + 6x) must leave a realistic operator workload:
  sources of every kind, a review queue, auto-matched RealProducts, duplicate
  groups, integration events and monitoring observations. Read-only.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Seeded sources are present with their kinds
    When I GET the v2 admin endpoint "atlas/admin/sources/"
    Then the response status should be 200
    And the results should contain an item with "idx" equal to "atl-nova"
    And the results should contain an item with "idx" equal to "atl-push"
    And the results should contain an item with "idx" equal to "atl-watch-de"
    And the results should contain an item with "idx" equal to "atl-watch-pl"
    And the results should contain an item with "idx" equal to "atl-signals"

  Scenario: atl-nova is a procurement source with the fixtures feed
    When I GET the v2 admin endpoint "atlas/admin/sources/atl-nova/"
    Then the response status should be 200
    And the response field "kind" should equal "procurement"
    And the response field "sku_prefix" should equal "ATL"
    And the response field "target_warehouse_code" should equal "atlas-wh"

  Scenario: The Swipe review queue is non-empty after seed
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value    |
      | status | queued   |
      | source | atl-nova |
    Then the response status should be 200
    And the results count should be greater than 3

  Scenario: Feed import pushed products exist
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value    |
      | status | pushed   |
      | source | atl-nova |
    Then the response status should be 200
    And the results count should be greater than 2

  Scenario: A rejected product exists for the requeue flow
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value    |
      | status | rejected |
      | source | atl-nova |
    Then the response status should be 200
    And the results should contain an item with "external_id" equal to "ATL-N012"

  Scenario: EAN auto-match left auto-matched RealProducts
    When I GET the v2 admin endpoint "atlas/admin/auto-matched/"
    Then the response status should be 200
    And the results should contain an item with "sku" equal to "ATL-ANCHOR-1"
    And the results should contain an item with "sku" equal to "ATL-ANCHOR-2"

  Scenario: Duplicate RealProduct groups are detected
    When I GET the v2 admin endpoint "atlas/admin/duplicates/"
    Then the response status should be 200
    And the results count should be greater than 1

  Scenario: The events feed carries the seeded tolerance violation
    When I GET the v2 admin endpoint "atlas/admin/events/" with params
      | param      | value                        |
      | event_type | physical_tolerance_violation |
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: Monitoring observations exist for catalogue products
    When I GET the v2 admin endpoint "atlas/admin/observations/" with params
      | param | value      |
      | kind  | monitoring |
    Then the response status should be 200
    # > 4 — the atlas workload alone seeds 5 monitoring rows; the pricefighter
    # seed (skipped on atlas-only environments) adds more on top.
    And the results count should be greater than 4
