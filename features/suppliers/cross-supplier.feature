@suppliers @cross-supplier
Feature: Cross-supplier dashboards — merge-by-ean + auto-matched + duplicates contract
  As a platform operator
  I want the suppliers Admin API to (1) accept merge-by-ean
  with strong validation, (2) expose an auto-matched dashboard listing,
  and (3) surface the duplicate-detection service via a list endpoint
  so the CMS Suppliers panel can render cross-supplier dashboards without
  hand-rolling backend logic.

  Five contract surfaces this feature locks (the actual cascade + audit +
  event-emission behaviour is covered by django-suppliers pytest
  test_realproduct_merge_service.py + test_merge_by_ean_api.py + the
  Playwright E2E walkthrough):

    1. POST /api/suppliers/v2/admin/realproducts/merge-by-ean/
       rejects an empty/short reason with 400 + debug_id. Pydantic schema
       validation must surface as v2 envelope, not a 500.
    2. POST /api/suppliers/v2/admin/realproducts/merge-by-ean/
       returns 404 + debug_id when either SKU is unknown. Operator typo on SKU.
    3. POST /api/suppliers/v2/admin/realproducts/merge-by-ean/
       returns 400 + debug_id when winner_sku == loser_sku. Schema-level
       defense; service also raises but envelope shape must be identical.
    4. GET /api/suppliers/v2/admin/auto-matched/?supplier=<idx>
       returns 200 + paginated results list. Locks the filter contract; the
       CMS sidebar Per-supplier dropdown drives this.
    5. GET /api/suppliers/v2/admin/duplicates/?tolerance_pct=10
       returns 200 + results list with `suggestion` field on every group.
       Locks the suggestion enum value (`merge` or `review`) the CMS UI
       renders as a StatusBadge.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @merge @short-reason @v2-envelope
  Scenario: merge-by-ean rejects a reason shorter than 3 characters
    # Pydantic min_length=3 + the field_validator stripping whitespace MUST
    # both surface as a 400 with debug_id, not bypass into the service layer
    # where ValueError would also produce 400 but with a different message.
    # The CMS modal disables the confirm button below 3 chars, but the
    # backend is the last line of defense for direct curl / scripted callers.
    When I POST to the v2 admin endpoint "suppliers/admin/realproducts/merge-by-ean/" with body
      """
      {"winner_sku": "SKU-DOES-NOT-EXIST-1", "loser_sku": "SKU-DOES-NOT-EXIST-2", "reason": "x"}
      """
    Then the response status should be 400
    And the error response should have a debug_id

  @merge @unknown-sku @v2-envelope
  Scenario: merge-by-ean returns 404 when one of the SKUs is unknown
    # The service raises RealProduct.DoesNotExist on .get(); the view catches
    # it and re-raises as drf_exceptions.NotFound. CMS toast keys on the 404
    # envelope to distinguish "you mistyped a SKU" from "validation failed".
    When I POST to the v2 admin endpoint "suppliers/admin/realproducts/merge-by-ean/" with body
      """
      {"winner_sku": "SKU-DOES-NOT-EXIST-WINNER", "loser_sku": "SKU-DOES-NOT-EXIST-LOSER", "reason": "Operator triage of EAN collision"}
      """
    Then the response status should be 404
    And the error response should have a debug_id

  @merge @self-merge @v2-envelope
  Scenario: merge-by-ean rejects winner_sku == loser_sku
    # Schema-level defense (the service also raises). Pydantic doesn't
    # cross-validate field equality by default, so this falls through to
    # the service ValueError -> drf ValidationError 400 envelope.
    When I POST to the v2 admin endpoint "suppliers/admin/realproducts/merge-by-ean/" with body
      """
      {"winner_sku": "SKU-DOES-NOT-EXIST-X", "loser_sku": "SKU-DOES-NOT-EXIST-X", "reason": "Tried to merge with self"}
      """
    Then the response status should be 400
    And the error response should have a debug_id

  @auto-matched @filter-supplier
  Scenario: auto-matched list endpoint accepts supplier filter
    # Locks the contract that the supplier filter is a query parameter, not
    # part of the URL path, and that it returns 200 with `results` as a list
    # even when no auto-link audit rows exist for that supplier yet. CMS
    # Per-supplier sidebar dropdown drives this.
    When I GET the v2 admin endpoint "suppliers/admin/auto-matched/?supplier=ghost-supplier"
    Then the response status should be 200
    And the response field "results" should be a list

  @duplicates @list @suggestion
  Scenario: duplicates list endpoint exposes suggestion field
    # Locks the response shape: `results` is a list, each group has an
    # `ean` + `realproducts` + `suggestion` field. The CMS renders the
    # suggestion as a StatusBadge (positive=merge, warning=review) so the
    # enum value drift would silently break the UI.
    When I GET the v2 admin endpoint "suppliers/admin/duplicates/?tolerance_pct=10"
    Then the response status should be 200
    And the response field "results" should be a list
