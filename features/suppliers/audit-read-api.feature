@suppliers @audit-read
Feature: Suppliers audit log — PIM SKU bridge (read API)
  As a platform operator
  I want to see the audit log timeline for a PIM SKU, bulk-check which SKUs
  have unseen supplier changes, acknowledge changes I'm not going to propagate,
  and force re-push by SKU
  So that the PIM list view can render "Updated" badges and the
  detail view can render a Supplier tab without each panel reaching
  into SupplierProduct PKs.

  This slice ships 4 new admin endpoints under `/suppliers/v2/admin/pim-sku/`.
  This feature locks the contract surface — auth boundary, request validation,
  v2 error envelope, response shape on the "no data" path. Deep verification
  (timeline with seeded novatrade SP, ack round-trip writing audit-of-audit row)
  belongs to the Playwright + SQL E2E sweep that runs after merge.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @timeline @v2-envelope
  Scenario: GET /pim-sku/{sku}/changes/ returns 404 with v2 envelope when SKU is unknown
    # Service raises ValueError("PIM SKU '...' not found.") — raise_as_drf maps
    # the "not found" suffix to 404. The v2 exception handler then wraps the
    # response in {error, message, debug_id, details} so CMS toasts get a
    # consistent shape.
    When I GET the v2 admin endpoint "suppliers/admin/pim-sku/UNKNOWN-SKU/changes/"
    Then the response status should be 404
    And the error response should have a debug_id

  @bulk
  Scenario: GET /pim-sku/has-changes/ bulk lookup returns a map keyed by SKU
    # Every requested SKU appears in the response — has_supplier=false for
    # unknown SKUs, never 404 or 400. The PIM list view will call this per
    # page (50 SKU) so absent rows must not break the badge render loop.
    When I GET the v2 admin endpoint "suppliers/admin/pim-sku/has-changes/?skus=UNKNOWN-A,UNKNOWN-B"
    Then the response status should be 200
    And the response field "skus" should be a dict
    And the response nested field "skus.UNKNOWN-A.has_supplier" should equal "False"
    And the response nested field "skus.UNKNOWN-B.has_supplier" should equal "False"

  @bulk @validation
  Scenario: GET /pim-sku/has-changes/ rejects empty skus param
    # Defensive: a missing query param shouldn't 500. The view raises
    # drf_exceptions.ValidationError → v2 handler emits 400 envelope.
    When I GET the v2 admin endpoint "suppliers/admin/pim-sku/has-changes/"
    Then the response status should be 400
    And the error response should have a debug_id

  @ack @v2-envelope
  Scenario: POST /pim-sku/{sku}/acknowledge/ requires exactly one of change_ids or all_unseen
    # Pydantic model_validator enforces exclusivity. raise_pydantic_as_drf
    # converts ValidationError to the v2 envelope. This is the only
    # client-visible contract on the ack endpoint that doesn't require
    # seeded audit rows.
    When I POST to the v2 admin endpoint "suppliers/admin/pim-sku/SOMESKU/acknowledge/" with body
      """
      {"change_ids": [1, 2], "all_unseen": true}
      """
    Then the response status should be 400
    And the error response should have a debug_id

  @force-repush
  Scenario: POST /pim-sku/{sku}/force-repush/ returns 404 when no active links exist
    # Service emits ValueError("No active supplier links for SKU '...' not found.")
    # whose " not found." tail steers raise_as_drf to 404. Operator gets a
    # crisp signal instead of a misleading 200/empty payload.
    When I POST to the v2 admin endpoint "suppliers/admin/pim-sku/UNKNOWN-SKU/force-repush/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id
