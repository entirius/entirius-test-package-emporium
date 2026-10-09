@access @admin @v2
Feature: Access administration — catalogue, custom roles, grants and the audit trail
  As an access administrator
  I want to compose roles from the catalogue and grant them to staff
  So that a permission is added and taken away by a grant, and every change is audited

  Scenario: AA-01 the catalogue offers 49 areas and 9 token scopes
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "access/admin/catalogue/"
    Then the response status should be 200
    And the catalogue should offer 49 areas and 9 token scopes

  Scenario: AA-02 a custom role granted to the viewer opens FAQ writes until the grant is revoked
    Given the channel is the primary channel
    And a run-unique suffix is saved as "saved.run"
    And I save the id of the viewer staff user as "saved.viewer_id"
    And I save the newest audit entry id as "saved.mark"
    And the admin sends DELETE to "access/admin/roles/{saved.role_id}/" when the scenario ends
    And the admin sends DELETE to "access/admin/grants/{saved.grant_id}/" when the scenario ends
    And the admin sends DELETE to "faq/admin/{channel_idx}/groups/bdd-access-{saved.run}/" when the scenario ends
    And I am authenticated as the viewer staff user
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/" with body
      """
      {"idx": "bdd-access-{saved.run}", "name": "BDD access {saved.run}"}
      """
    Then the gate refuses with issue "ACCESS_DENIED"
    Given I am authenticated as an admin user
    When I POST to the v2 admin endpoint "access/admin/roles/" with body
      """
      {"key": "bdd-access-{saved.run}", "name": "BDD FAQ writer {saved.run}", "permissions": ["faq.faq:write"]}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.role_id"
    When I POST to the v2 admin endpoint "access/admin/grants/" with body
      """
      {"role": "bdd-access-{saved.run}", "user_id": {saved.viewer_id}}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.grant_id"
    Given I am authenticated as the viewer staff user
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/" with body
      """
      {"idx": "bdd-access-{saved.run}", "name": "BDD access {saved.run}"}
      """
    Then the response status should be 201
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/groups/bdd-access-{saved.run}/"
    Then the response status should be 204
    Given I am authenticated as an admin user
    When I DELETE the v2 admin endpoint "access/admin/grants/{saved.grant_id}/"
    Then the response status should be 204
    Given I am authenticated as the viewer staff user
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/groups/" with body
      """
      {"idx": "bdd-access-{saved.run}", "name": "BDD access {saved.run}"}
      """
    Then the gate refuses with issue "ACCESS_DENIED"
    And the audit log has a "role.create" entry after "saved.mark" for target "{saved.role_id}"
    And the audit log has a "grant.create" entry after "saved.mark" for target "{saved.grant_id}"

  Scenario: AA-03 a built-in role cannot be changed
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "access/admin/roles/"
    Then the response status should be 200
    And I save the id of the result with "key" equal to "viewer" as "saved.viewer_role_id"
    When I PATCH the v2 admin endpoint "access/admin/roles/{saved.viewer_role_id}/" with body
      """
      {"name": "Not the viewer"}
      """
    Then the response status should be 409
    And the error response should have error code "CONFLICT"

  Scenario: AA-04 a superuser write through the gate leaves a gate.bypass audit entry
    Given a run-unique suffix is saved as "saved.run"
    And I save the newest audit entry id as "saved.mark"
    And the admin sends DELETE to "access/admin/roles/{saved.role_id}/" when the scenario ends
    And I am authenticated as an admin user
    When I POST to the v2 admin endpoint "access/admin/roles/" with body
      """
      {"key": "bdd-bypass-{saved.run}", "name": "BDD bypass {saved.run}", "permissions": ["faq.faq:read"]}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.role_id"
    And the audit log has a "gate.bypass" entry after "saved.mark" for POST "api/access/v2/admin/roles/"

  Scenario: AA-05 a superuser read leaves no gate.bypass audit entry
    Given I save the newest audit entry id as "saved.mark"
    And I am authenticated as an admin user
    When I GET the v2 admin endpoint "access/admin/roles/"
    Then the response status should be 200
    And the audit log has no "gate.bypass" entry after "saved.mark"
