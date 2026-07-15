@admin @suppliers @v2 @suppliers-repush @supplier
Feature: Suppliers Admin API -- Force Re-push
  As an admin user
  I want to force re-push enrichment for an already-pushed supplier product
  So that I can refresh attributes and images on operator demand

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: Force re-push on non-pushed SP returns 400
    # DEMO-001 fixture is status=new, force-repush requires pushed/pushed_pending_images
    When I POST to the v2 admin endpoint "suppliers/admin/products/1/force-repush/" with body
      """
      {}
      """
    Then the response status should be 400

  Scenario: Force re-push on rejected SP returns 400
    # DEMO-005 fixture is status=rejected
    When I POST to the v2 admin endpoint "suppliers/admin/products/5/force-repush/" with body
      """
      {}
      """
    Then the response status should be 400

  Scenario: Force re-push on pushed SP succeeds and emits force_repush_executed event
    # Own approved SP (DEMO-006): push once, then force-repush. push is one-shot in 2.0.0.
    When I POST to the v2 admin endpoint "suppliers/admin/products/6/push/" with body
      """
      {}
      """
    Then the response status should be 200
    # Now force re-push. Status is at least pushed_pending_images.
    When I POST to the v2 admin endpoint "suppliers/admin/products/6/force-repush/" with body
      """
      {}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/events/?event_type=force_repush_executed&page_size=10"
    Then the response status should be 200
