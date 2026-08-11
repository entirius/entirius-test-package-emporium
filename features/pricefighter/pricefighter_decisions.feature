@pricefighter @v2 @decisions
Feature: PriceFighter Admin API -- decision list and detail
  Sort allowlist, filters validated against live markets, detail with the full
  flagged observation list. Read-only.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Unknown sort field is refused
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/" with params
      | param | value          |
      | sort  | drop_table_lol |
    Then the response status should be 400

  Scenario: Unknown channel filter is refused
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/" with params
      | param   | value        |
      | channel | no-such-chan |
    Then the response status should be 400

  Scenario: Unknown recommendation filter is refused
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/" with params
      | param          | value  |
      | recommendation | yolo   |
    Then the response status should be 400

  Scenario: Recommendation filter narrows the list
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/" with params
      | param          | value |
      | recommendation | raise |
    Then the response status should be 200
    And the results should not contain an item with "recommendation" equal to "compete"

  Scenario: Detail requires the market coordinates
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/ENT-C001/"
    Then the response status should be 400

  Scenario: Detail returns the flagged observation list
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/ENT-C001/" with params
      | param    | value          |
      | channel  | default-europe |
      | country  | DE             |
      | currency | EUR            |
    Then the response status should be 200
    And the response field "recommendation" should equal "compete"
    And the response field "observations" should be a list
