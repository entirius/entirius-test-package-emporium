@pricefighter @v2 @apply
Feature: PriceFighter Admin API -- batch apply
  Apply recomputes each decision live and buckets every item: applied, stale,
  skipped (not actionable / guard-refused), clamped, failed. Scenarios re-read
  the live suggestion first, so they stay green on re-runs (an already-applied
  price recomputes to the same suggestion).

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Applying the live suggestion writes the price
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/ENT-C002/" with params
      | param    | value          |
      | channel  | default-europe |
      | country  | DE             |
      | currency | EUR            |
    Then the response status should be 200
    And I save the response field "suggested_price" as "target_price"
    When I POST to the v2 admin endpoint "pricefighter/admin/apply/" with body
      """
      {"items": [{"sku": "ENT-C002",
                  "market": {"channel": "default-europe", "country": "DE", "currency": "EUR"},
                  "expected_new_price": "{target_price}"}]}
      """
    Then the response status should be 200
    And the response field "failed" should be an empty list
    And the response field "stale" should be an empty list
    And the response nested field "applied.0.sku" should equal "ENT-C002"

  Scenario: A stale expected price is refused without writing
    When I POST to the v2 admin endpoint "pricefighter/admin/apply/" with body
      """
      {"items": [{"sku": "ENT-C002",
                  "market": {"channel": "default-europe", "country": "DE", "currency": "EUR"},
                  "expected_new_price": "1.00"}]}
      """
    Then the response status should be 200
    And the response field "applied" should be an empty list
    And the response nested field "stale.0.sku" should equal "ENT-C002"

  Scenario: An in-band hold is not actionable
    When I POST to the v2 admin endpoint "pricefighter/admin/apply/" with body
      """
      {"items": [{"sku": "ENT-O002",
                  "market": {"channel": "default-europe", "country": "DE", "currency": "EUR"},
                  "expected_new_price": "355.00"}]}
      """
    Then the response status should be 200
    And the response field "applied" should be an empty list
    And the response nested field "skipped.0.sku" should equal "ENT-O002"

  Scenario: An admin-owned price is never overwritten
    When I GET the v2 admin endpoint "pricefighter/admin/decisions/ENT-C001/" with params
      | param    | value          |
      | channel  | default-europe |
      | country  | FR             |
      | currency | EUR            |
    Then the response status should be 200
    And I save the response field "suggested_price" as "fr_price"
    When I POST to the v2 admin endpoint "pricefighter/admin/apply/" with body
      """
      {"items": [{"sku": "ENT-C001",
                  "market": {"channel": "default-europe", "country": "FR", "currency": "EUR"},
                  "expected_new_price": "{fr_price}"}]}
      """
    Then the response status should be 200
    And the response field "applied" should be an empty list
    And the response nested field "skipped.0.sku" should equal "ENT-C001"

  Scenario: An unknown market fails cleanly
    When I POST to the v2 admin endpoint "pricefighter/admin/apply/" with body
      """
      {"items": [{"sku": "ENT-C002",
                  "market": {"channel": "no-such-chan", "country": "DE", "currency": "EUR"},
                  "expected_new_price": "10.00"}]}
      """
    Then the response status should be 200
    And the response field "applied" should be an empty list
    And the response nested field "failed.0.sku" should equal "ENT-C002"

  Scenario: An empty items list is a validation error
    When I POST to the v2 admin endpoint "pricefighter/admin/apply/" with body
      """
      {"items": []}
      """
    Then the response status should be 400
