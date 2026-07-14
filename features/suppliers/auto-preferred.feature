@suppliers @preferred-strategy
Feature: Auto-preferred selection — manual override + reset + event filter contracts
  As a platform operator
  I want the suppliers Admin API to (1) accept set-preferred-supplier
  with strong validation, (2) expose reset-preferred-to-auto, and (3)
  surface every new IntegrationEvent type as a filter on the events list
  so the CMS Events panel can render them without backend code drift.

  Five contract surfaces this feature locks (the actual switch + cooldown +
  hysteresis behaviour is covered by django-suppliers pytest
  test_preferred_strategy_service.py + test_preferred_eval_cron.py + the
  Playwright E2E walkthrough):

    1. POST /api/suppliers/v2/admin/pim-sku/{sku}/set-preferred-supplier/
       rejects an empty/short reason with 400 + debug_id. Pydantic schema
       validation must surface as v2 envelope, not a 500.
    2. POST /api/suppliers/v2/admin/pim-sku/{sku}/set-preferred-supplier/
       returns 404 + debug_id when the (sku, supplier_idx) pair has no
       active ProductSupplierLink. Operator typo on supplier_idx.
    3. POST /api/suppliers/v2/admin/pim-sku/{sku}/reset-preferred-to-auto/
       returns 404 + debug_id when the SKU has no active link at all.
       Same envelope shape as set-preferred-supplier.
    4. GET /api/suppliers/v2/admin/events/?event_type=preferred_supplier_switched
       returns 200 + paginated results list. Locks the EventType enum value.
    5. GET /api/suppliers/v2/admin/events/?event_type=preferred_supplier_emergency_switch
       returns 200 + paginated results list. Locks the second new EventType.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @set-preferred @short-reason @v2-envelope
  Scenario: set-preferred-supplier rejects a reason shorter than 3 characters
    # Pydantic min_length=3 + the field_validator stripping whitespace MUST
    # both surface as a 400 with debug_id, not bypass into the service layer
    # where ValueError would also produce 400 but with a different message.
    # The CMS modal disables the confirm button below 3 chars, but the
    # backend is the last line of defense for direct curl / scripted callers.
    When I POST to the v2 admin endpoint "suppliers/admin/pim-sku/SKU-DOES-NOT-EXIST/set-preferred-supplier/" with body
      """
      {"supplier_idx": "ghost", "reason": "x"}
      """
    Then the response status should be 400
    And the error response should have a debug_id

  @set-preferred @unknown-supplier @v2-envelope
  Scenario: set-preferred-supplier returns 404 when (sku, supplier_idx) has no link
    # The service raises ValueError("...not found"); raise_as_drf maps it to
    # NotFound by the suffix rule. CMS toast keys on the 404 envelope.
    When I POST to the v2 admin endpoint "suppliers/admin/pim-sku/SKU-DOES-NOT-EXIST/set-preferred-supplier/" with body
      """
      {"supplier_idx": "ghost-supplier", "reason": "manual override audit text"}
      """
    Then the response status should be 404
    And the error response should have a debug_id

  @reset-to-auto @no-link @v2-envelope
  Scenario: reset-preferred-to-auto returns 404 when the SKU has no active link
    # Mirror of the unknown-supplier scenario above for the reset endpoint.
    # The view checks _sku_has_active_link() before delegating to the
    # service so the 404 envelope is identical to set-preferred-supplier.
    When I POST to the v2 admin endpoint "suppliers/admin/pim-sku/SKU-DOES-NOT-EXIST/reset-preferred-to-auto/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id

  @events @preferred-switched @filter
  Scenario: events list endpoint accepts preferred_supplier_switched filter
    # Lock the EventType.PREFERRED_SUPPLIER_SWITCHED registration. If the
    # enum value is missing or renamed, the validator on the events list
    # endpoint would crash. Empty results are fine; test-package doesn't
    # exercise the auto-preferred switch path.
    When I GET the v2 admin endpoint "suppliers/admin/events/?event_type=preferred_supplier_switched"
    Then the response status should be 200
    And the response field "results" should be a list

  @events @preferred-emergency @filter
  Scenario: events list endpoint accepts preferred_supplier_emergency_switch filter
    # Symmetric to the previous scenario, locks the second new EventType.
    # This one is severity=warning — operator playbook flags it as a flag
    # for "preferred lost stock; storefront just flipped on its own".
    When I GET the v2 admin endpoint "suppliers/admin/events/?event_type=preferred_supplier_emergency_switch"
    Then the response status should be 200
    And the response field "results" should be a list
