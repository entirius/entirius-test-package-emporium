@access @access-security
Feature: Access security — superuser writes leave an audit row, reads do not
  As the platform's security owner
  I want every superuser write that passes the gate on its bypass recorded with its outcome
  So that the one principal the gate never refuses still leaves a trail

  Counted after a mark (the newest audit id), for this run's route and method only. A GET PII export counts as a write.

  Scenario: AU-01 a superuser role create leaves one gate.bypass row with its status and one role.create row
    Given a run-unique suffix is saved as "saved.run"
    And the role "bdd-audit-{saved.run}" is deleted when the scenario ends
    And I save the newest audit entry id as "saved.mark"
    And the caller is admin
    When the caller sends POST to "api/access/v2/admin/roles/" with body
      """
      {"key": "bdd-audit-{saved.run}", "name": "BDD audit {saved.run}", "permissions": ["faq.faq:read"]}
      """
    Then the answer is 201 with "-"
    And I save the response field "id" as "saved.role"
    And the audit log counts 1 "gate.bypass" after "saved.mark" for POST "api/access/v2/admin/roles/" with status 201
    And the audit log counts 1 "role.create" after "saved.mark" for target "{saved.role}"

  Scenario: AU-02 a superuser GET of a PII export leaves one gate.bypass row
    Given I save the newest audit entry id as "saved.mark"
    And the caller is admin
    When the caller sends GET to "api/agreements/v2/admin/marketing-subscribers/export/"
    Then the answer is 200 with "-"
    And the audit log counts 1 "gate.bypass" after "saved.mark" for GET "api/agreements/v2/admin/marketing-subscribers/export/" with status 200

  Scenario: AU-03 a superuser read leaves no gate.bypass row
    Given I save the newest audit entry id as "saved.mark"
    And the caller is admin
    When the caller sends GET to "api/access/v2/admin/roles/"
    Then the answer is 200 with "-"
    And the audit log counts 0 "gate.bypass" after "saved.mark" for GET "api/access/v2/admin/roles/"
