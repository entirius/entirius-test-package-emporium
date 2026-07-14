@suppliers @error-feedback
Feature: Suppliers admin error feedback — v2 envelope on every failure
  As the CMS Blueprint operator
  I want every backend error to come back in the v2 shape `{error, message, debug_id, details}`
  So that the global apiClient interceptor can render toasts + inline errors
  uniformly across all suppliers admin endpoints.

  Previously, suppliers admin views
  caught service-layer `ValueError` and returned `{detail: str(e)}` with status 400/404,
  bypassing the v2 exception handler. Frontend therefore had to special-case suppliers
  vs PIM/Matrix error shapes. Now every endpoint emits the canonical v2
  envelope and the frontend can extract `response.data.message` uniformly.

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  @toast @v2-envelope
  Scenario: POST attribute mapping with bogus target_identifier returns v2 envelope
    # CMS prevents this in 99% of cases (autocomplete on target_identifier dropdown).
    # But a stale browser tab / direct curl can still hit it — the response shape
    # must be parseable by the global frontend interceptor regardless.
    Given I ensure mapping profile "bdd-toast" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/mapping-profiles/" with body
      """
      {
        "idx": "bdd-toast",
        "name": "Toast scenario",
        "target_channel_idxs": ["{channel_idx}"],
        "is_active": false
      }
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.profile_pk"
    When I POST to the v2 admin endpoint "suppliers/admin/mapping-profiles/{saved.profile_pk}/attribute-mappings/" with body
      """
      {
        "source_field": "__name__",
        "target_type": "feature",
        "target_identifier": "nonexistent_feature_xyz",
        "is_required": false
      }
      """
    # Service raises ValueError("Feature 'nonexistent_feature_xyz' not found") which
    # _helpers.raise_as_drf converts to NotFound (resource prefix match) → 404.
    Then the response status should be 404
    And the error response should have error code "NOT_FOUND"
    And the error response should have a debug_id
    Given I ensure mapping profile "bdd-toast" for supplier "demo-supplier" is cleaned up

  @auth-retry @v2-envelope
  Scenario: GET admin endpoint without auth returns v2 envelope (401)
    # Verifies the v2 exception handler kicks in for AuthenticationRequired too.
    # The CMS apiClient interceptor uses this to trigger auto-refresh + retry.
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/" without auth
    Then the response status should be 401
    And the error response should have error code "AUTHENTICATION_REQUIRED"
    And the error response should have a debug_id
