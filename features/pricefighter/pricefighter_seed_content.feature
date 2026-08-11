@pricefighter @v2 @seed-content
Feature: PriceFighter seed content contract
  The decision queue is computed live from seeded inputs (costs, baseline, quote
  config, rules, monitoring observations). After the full seed the operator must
  see every recommendation type plus a non-empty apply history. Read-only.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Channels are synced from PIM
    When I GET the v2 admin endpoint "pricefighter/admin/channels/"
    Then the response status should be 200
    And the results should contain an item with "idx" equal to "default-europe"

  Scenario: Pricing rules are seeded
    When I GET the v2 admin endpoint "pricefighter/admin/rules/"
    Then the response status should be 200
    And the results count should be greater than 2

  Scenario: The decision list is non-empty
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/"
    Then the response status should be 200
    And the results count should be greater than 5

  Scenario: A compete recommendation is present
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/" with params
      | param          | value   |
      | recommendation | compete |
    Then the response status should be 200
    And the results should contain an item with "sku" equal to "ENT-C002"

  Scenario: A raise recommendation is present
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/" with params
      | param          | value |
      | recommendation | raise |
    Then the response status should be 200
    And the results should contain an item with "sku" equal to "ENT-D001"

  Scenario: A price-war floor hold is present
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/" with params
      | param          | value         |
      | recommendation | hold_at_floor |
    Then the response status should be 200
    And the results should contain an item with "sku" equal to "ENT-O001"

  Scenario: A product without cost yields no_recommendation
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/" with params
      | param          | value             |
      | recommendation | no_recommendation |
    Then the response status should be 200
    And the results should contain an item with "sku" equal to "ENT-B001"

  Scenario: Apply history carries the seeded writes
    When I GET the v2 admin endpoint "pricefighter/admin/history/"
    Then the response status should be 200
    And the results count should be greater than 2
    And the results should contain an item with "strategy" equal to "revert_baseline"
