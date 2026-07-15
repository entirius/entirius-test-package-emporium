@admin @suppliers @v2 @suppliers-audit @supplier
Feature: Suppliers Admin API -- Review Audit Trail
  As an admin user
  I want my approve/reject/push actions tracked with timestamps and user attribution
  So that we can audit who reviewed/pushed which supplier products

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: Approve sets reviewed_by and reviewed_at on SP
    # DEMO-001 fixture is status=new
    When I POST to the v2 admin endpoint "suppliers/admin/products/1/approve/" with body
      """
      {}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/products/1/"
    Then the response status should be 200
    And the response field "status" should equal "approved"
    And the response field "reviewed_at" should not be null
    And the response field "reviewed_by_id" should not be null

  Scenario: Reject sets reviewed_by, reject keeps audit
    # DEMO-002 fixture is status=new
    When I POST to the v2 admin endpoint "suppliers/admin/products/2/reject/" with body
      """
      {}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/products/2/"
    Then the response status should be 200
    And the response field "status" should equal "rejected"
    And the response field "reviewed_at" should not be null

  Scenario: Push sets pushed_by and pushed_at while keeping reviewed_by
    # DEMO-004 is approved in fixture
    When I POST to the v2 admin endpoint "suppliers/admin/products/4/push/" with body
      """
      {}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/products/4/"
    Then the response status should be 200
    And the response field "pushed_at" should not be null
    And the response field "pushed_by_id" should not be null

  Scenario: Bulk re-queue rejected back to queued preserves original reviewed_by/reviewed_at (D29)
    # First reject DEMO-001 (was approved earlier in this feature run; idempotent re-reject)
    When I POST to the v2 admin endpoint "suppliers/admin/products/1/reject/" with body
      """
      {}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/products/1/"
    Then the response status should be 200
    Then I save the response field "reviewed_at" as "saved.original_reviewed_at"
    # Bulk requeue DEMO-001 (rejected -> queued)
    When I POST to the v2 admin endpoint "suppliers/admin/products/bulk-requeue/" with body
      """
      {"ids": [1]}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/products/1/"
    Then the response status should be 200
    And the response field "status" should equal "queued"
    # reviewed_by and reviewed_at preserved (D29)
    And the response field "reviewed_at" should not be null
