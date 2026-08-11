@atlas @v2 @review
Feature: Atlas Admin API -- review status transitions
  The review lifecycle: new -> queued -> approved/rejected, rejected -> queued.
  Monitoring products may only be rejected. All addressing by source + external_id
  (natural keys) via the products list filters -- never by hardcoded PK.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Queue then approve a fresh atl-nova product
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value    |
      | source | atl-nova |
      | search | ATL-N010 |
    Then the response status should be 200
    And I save the first result field "id" as "sp_id"
    When I POST to the v2 admin endpoint "atlas/admin/products/{sp_id}/queue/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "status" should equal "queued"
    When I POST to the v2 admin endpoint "atlas/admin/products/{sp_id}/approve/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "status" should equal "approved"

  Scenario: Approved product can be rejected and requeued
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value    |
      | source | atl-nova |
      | search | ATL-N010 |
    Then I save the first result field "id" as "sp_id"
    When I POST to the v2 admin endpoint "atlas/admin/products/{sp_id}/reject/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "status" should equal "rejected"
    When I POST to the v2 admin endpoint "atlas/admin/products/{sp_id}/queue/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "status" should equal "queued"

  Scenario: Skip returns a queued product to new
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value    |
      | source | atl-nova |
      | search | ATL-N010 |
    Then I save the first result field "id" as "sp_id"
    When I POST to the v2 admin endpoint "atlas/admin/products/{sp_id}/skip/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "status" should equal "new"

  Scenario: Rejecting a pushed product is an invalid transition
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value    |
      | status | pushed   |
      | source | atl-nova |
    Then I save the first result field "id" as "sp_id"
    When I POST to the v2 admin endpoint "atlas/admin/products/{sp_id}/queue/" with body
      """
      {}
      """
    Then the response status should be 400

  Scenario: Bulk requeue moves rejected products back to the queue
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value    |
      | status | rejected |
      | source | atl-nova |
      | search | ATL-N012 |
    Then I save the first result field "id" as "sp_id"
    When I POST to the v2 admin endpoint "atlas/admin/products/bulk-requeue/" with body
      """
      {"ids": [{sp_id}]}
      """
    Then the response status should be 200
    When I POST to the v2 admin endpoint "atlas/admin/products/bulk-reject/" with body
      """
      {"ids": [{sp_id}]}
      """
    Then the response status should be 200
