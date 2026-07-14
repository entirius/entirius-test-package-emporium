@suppliers @auto-ean-match
Feature: Auto EAN-match in init_push + unlink escape hatch
  As a platform operator
  I want the suppliers Admin API to (1) expose an unlink-from-realproduct
  endpoint that lets me undo an auto-linked SP, and (2) accept the new
  IntegrationEvent types (auto_linked_to_existing_realproduct,
  physical_tolerance_violation) as query filters so the CMS Events panel can
  surface them without backend code drift.

  Three contract surfaces this feature locks (the actual auto-link behaviour
  is covered by django-suppliers pytest test_init_push_auto_link.py + the
  Playwright E2E walkthrough):

    1. POST /api/suppliers/v2/admin/products/{pk}/unlink-from-realproduct/
       returns 404 + debug_id when pk is unknown. Mirrors the v2 envelope
       contract from force-repush / quick-approve so CMS toast logic keys
       on a single error shape.
    2. GET /api/suppliers/v2/admin/events/?event_type=auto_linked_to_existing_realproduct
       returns 200 + paginated results list. Proves the event_type is in the
       EventType enum and queryable through the existing list endpoint.
    3. GET /api/suppliers/v2/admin/events/?event_type=physical_tolerance_violation
       returns 200 + paginated results list (same contract, second new type).

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @products @unlink @unknown-pk @v2-envelope
  Scenario: unlink-from-realproduct returns 404 + debug_id for unknown SupplierProduct pk
    # Lock the CMS row-action contract: operator clicks unlink on a stale row
    # → POST → either 200 (happy path, exercised in pytest + Playwright) or
    # 404 (unknown SP). 404 + debug_id keeps the CMS toast logic uniform with
    # the rest of the v2 surface.
    When I POST to the v2 admin endpoint "suppliers/admin/products/99999999/unlink-from-realproduct/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id

  @events @auto-link-event @filter
  Scenario: events list endpoint accepts auto_linked_to_existing_realproduct filter
    # Lock the EventType.AUTO_LINKED_TO_EXISTING_REALPRODUCT registration —
    # if the enum value is missing or renamed, this filter call would crash
    # at the validator level. Empty results are fine; test package doesn't
    # exercise the auto-link path.
    When I GET the v2 admin endpoint "suppliers/admin/events/?event_type=auto_linked_to_existing_realproduct"
    Then the response status should be 200
    And the response field "results" should be a list

  @events @tolerance-violation @filter
  Scenario: events list endpoint accepts physical_tolerance_violation filter
    # Symmetric to the previous scenario, locks the second new EventType.
    When I GET the v2 admin endpoint "suppliers/admin/events/?event_type=physical_tolerance_violation"
    Then the response status should be 200
    And the response field "results" should be a list
