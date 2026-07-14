@suppliers @physical-race
Feature: Multi-supplier physical race detection — preferred-only writes + opt-in overwrite
  As a platform operator
  I want the suppliers Admin API to (1) round-trip the per-supplier opt-in flag
  `allow_physical_writes_from_non_preferred`, and (2) surface the two new
  IntegrationEvent types as valid filters on the events list
  so the CMS Overview tab can persist the operator's choice and the Events panel
  can render race-detect entries without backend code drift.

  Five contract surfaces this feature locks (the actual race-detect behaviour is
  covered by django-suppliers pytest test_physical_race.py + test_delta_sync_race.py
  + the Playwright E2E walkthrough):

    1. GET /api/suppliers/v2/admin/suppliers/{idx}/ includes the flag in the
       response schema (default false on the seeded test-package supplier).
    2. GET /api/suppliers/v2/admin/events/?event_type=physical_update_skipped_non_preferred
       returns 200 + paginated results list. Locks the EventType enum value.
    3. GET /api/suppliers/v2/admin/events/?event_type=physical_update_overwrite
       returns 200 + paginated results list. Locks the second new EventType.
    4. PATCH /api/suppliers/v2/admin/suppliers/{idx}/ accepts the boolean
       `allow_physical_writes_from_non_preferred` field and persists it.
       Returns 200 + the updated supplier object with true in the response.
    5. PATCH ... with the flag flipped back to false returns 200 + false in
       the response. Same envelope shape — locks the round-trip and resets
       the test-package supplier state.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @supplier-flag @response-shape
  Scenario: GET supplier includes allow_physical_writes_from_non_preferred in the response
    # Lock the SupplierResponse schema addition. When the field is added to the
    # request schema but missing from the response, the CMS OverviewTab silently
    # shows the default (false) on every load — a known knob-drift failure mode
    # seen before. This scenario guards against the same drift.
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/novatrade/"
    Then the response status should be 200
    And the response field "allow_physical_writes_from_non_preferred" should be false

  @events @physical-skipped @filter
  Scenario: events list endpoint accepts physical_update_skipped_non_preferred filter
    # Locks EventType.PHYSICAL_UPDATE_SKIPPED_NON_PREFERRED registration. The validator
    # on the events list endpoint would 400 if the enum value is missing or renamed.
    # Empty results are fine — test-package doesn't trigger a race event.
    When I GET the v2 admin endpoint "suppliers/admin/events/?event_type=physical_update_skipped_non_preferred"
    Then the response status should be 200
    And the response field "results" should be a list

  @events @physical-overwrite @filter
  Scenario: events list endpoint accepts physical_update_overwrite filter
    # Symmetric to the previous scenario — locks the second new EventType.
    # This one is severity=warning; the operator playbook flags it as "non-preferred
    # supplier overwrote RealProduct physical fields (opt-in)".
    When I GET the v2 admin endpoint "suppliers/admin/events/?event_type=physical_update_overwrite"
    Then the response status should be 200
    And the response field "results" should be a list

  @supplier-flag @patch-true @v2-envelope
  Scenario: PATCH supplier accepts allow_physical_writes_from_non_preferred=true
    When I PATCH the v2 admin endpoint "suppliers/admin/suppliers/novatrade/" with body
      """
      {"allow_physical_writes_from_non_preferred": true}
      """
    Then the response status should be 200
    And the response field "allow_physical_writes_from_non_preferred" should be true

  @supplier-flag @patch-false @v2-envelope
  Scenario: PATCH supplier flips allow_physical_writes_from_non_preferred back to false (reset)
    When I PATCH the v2 admin endpoint "suppliers/admin/suppliers/novatrade/" with body
      """
      {"allow_physical_writes_from_non_preferred": false}
      """
    Then the response status should be 200
    And the response field "allow_physical_writes_from_non_preferred" should be false
