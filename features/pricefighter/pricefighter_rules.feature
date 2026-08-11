@pricefighter @v2 @rules
Feature: PriceFighter Admin API -- pricing rule CRUD
  A rule is scoped to exactly one of sku / category / channel; without any rule
  the engine holds everything, so rules are the workload on/off switch.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Create, update and delete a sku-scoped rule
    When I POST to the v2 admin endpoint "pricefighter/admin/rules/" with body
      """
      {"strategy": "compete", "mode": "suggestion", "sku": "BDD-RULE-SKU"}
      """
    Then the response status should be 201
    And I save the response field "id" as "rule_id"
    When I PATCH the v2 admin endpoint "pricefighter/admin/rules/{rule_id}/" with body
      """
      {"strategy": "raise"}
      """
    Then the response status should be 200
    And the response field "strategy" should equal "raise"
    When I DELETE the v2 admin endpoint "pricefighter/admin/rules/{rule_id}/"
    Then the response status should be 204

  Scenario: A rule with two scopes is refused
    When I POST to the v2 admin endpoint "pricefighter/admin/rules/" with body
      """
      {"strategy": "compete", "sku": "BDD-RULE-SKU", "category_idx": "chairs"}
      """
    Then the response status should be 400

  Scenario: A rule with no scope is refused
    When I POST to the v2 admin endpoint "pricefighter/admin/rules/" with body
      """
      {"strategy": "compete"}
      """
    Then the response status should be 400

  Scenario: A rule pointing at an unknown channel is refused
    When I POST to the v2 admin endpoint "pricefighter/admin/rules/" with body
      """
      {"strategy": "compete", "channel": "no-such-chan"}
      """
    Then the response status should be 400
