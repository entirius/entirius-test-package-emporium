@suppliers @audit-log
Feature: Suppliers audit log — change_log_retention_days settings contract
  As a platform operator
  I want the SupplierProductChangeLog retention window to be a first-class
  setting alongside integration_event_retention_days
  So that the Celery prune task and the planned PIM-side change-indicator
  badges have a stable, surfaced knob.

  This slice is the audit-log foundation: new model + 6 write paths +
  retention task. The read API (`/pim-sku/{sku}/changes/`, `has-changes/`) lands
  separately, so deep audit-row verification belongs in the Playwright + SQL
  E2E sweep. This BDD locks the only API surface this slice exposes — the
  settings singleton — and proves the v2 envelope still wraps validation
  errors on the new field.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @settings @v2-envelope
  Scenario: GET /settings/ surfaces the new change_log_retention_days field
    # Migration 0007 added the field with default=90. Pydantic response schema
    # must expose it so the future CMS settings panel can render the knob.
    When I GET the v2 admin endpoint "suppliers/admin/settings/"
    Then the response status should be 200
    And the response field "change_log_retention_days" should not be null

  @settings @retention
  Scenario: PATCH /settings/ accepts a new change_log_retention_days value
    # Round-trip: write → read-back matches. Proves _EDITABLE_FIELDS includes
    # the new key (otherwise update_settings raises ValueError → 400).
    When I PATCH the v2 admin endpoint "suppliers/admin/settings/" with body
      """
      {"change_log_retention_days": 30}
      """
    Then the response status should be 200
    And the response field "change_log_retention_days" should equal integer 30
    When I PATCH the v2 admin endpoint "suppliers/admin/settings/" with body
      """
      {"change_log_retention_days": 90}
      """
    Then the response status should be 200
    And the response field "change_log_retention_days" should equal integer 90

  @settings @validation @v2-envelope
  Scenario: PATCH /settings/ with negative days returns v2 envelope
    # Pydantic ge=0 validator rejects negative values. The v2 exception handler
    # must wrap it in the canonical envelope so the frontend interceptor can
    # extract `message` uniformly with other suppliers errors.
    When I PATCH the v2 admin endpoint "suppliers/admin/settings/" with body
      """
      {"change_log_retention_days": -1}
      """
    Then the response status should be 400
    And the error response should have a debug_id
