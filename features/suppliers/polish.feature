@suppliers @polish
Feature: Polish cleanup — per-row quick approve + ImportLog count split
  As a platform operator
  I want the suppliers Admin API to (1) accept per-SP approve/reject calls so
  the CMS ProductsTab can ship row-level quick actions, and (2) surface
  per-run pushed-product delisting counts and the >50% mass-delisting flag on
  the ImportLog list response so dashboards don't have to recompute them.

  Two contract surfaces this feature locks (the rest is covered by django-suppliers
  pytest + cms-blueprint vitest + Playwright E2E):

    1. POST /api/suppliers/v2/admin/products/{pk}/approve/ exists, returns 404
       + debug_id when pk is unknown (does NOT 400 — important for the CMS
       ProductsTab row-action error toast which keys on v2 envelope).
    2. GET /api/suppliers/v2/admin/import-logs/ — every result carries the
       additive fields `pushed_delisted_count` (int) and
       `mass_delisting_triggered` (bool), present in the response shape even
       when no delisting happened (default 0 / False).

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @products @quick-approve @unknown-pk @v2-envelope
  Scenario: per-row approve endpoint returns 404 + debug_id for unknown SupplierProduct pk
    # Lock the CMS row-action contract: quickApprove(row) → POST → either 200
    # (happy path, exercised in vitest + Playwright) or 404 (unknown row, the
    # operator's stale page). 404 + debug_id keeps the CMS toast logic uniform
    # with the rest of the v2 surface; a 400 would break extractApiMessage().
    When I POST to the v2 admin endpoint "suppliers/admin/products/99999999/approve/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id

  @products @quick-reject @unknown-pk @v2-envelope
  Scenario: per-row reject endpoint returns 404 + debug_id for unknown SupplierProduct pk
    # Symmetric to quick-approve; same contract reason.
    When I POST to the v2 admin endpoint "suppliers/admin/products/99999999/reject/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id

  @import-log @pushed-delisted-counts
  Scenario: ImportLog list response carries pushed_delisted_count + mass_delisting_triggered
    # Lock the additive shape on ImportLogResponse (fields present, at defaults 0/False when no
    # pushed product was delisted). Trigger our OWN feed run so the newest ImportLog is one we
    # control — demo-supplier has no pushed SPs (push scenarios use bdd-push-sup), so this import
    # delists nothing. Reading results.0 right after our own trigger avoids depending on the delist
    # counts of other features' earlier runs.
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/main-catalog/trigger/" with body
      """
      {"mode": "full", "async": false}
      """
    Then the response status should be 200
    And the response field "run_id" should not be null
    When I GET the v2 admin endpoint "suppliers/admin/import-logs/"
    Then the response status should be 200
    And the response field "results" should be a list
    And the response nested field "results.0.pushed_delisted_count" should equal integer 0
    And the response nested field "results.0.mass_delisting_triggered" should be false
