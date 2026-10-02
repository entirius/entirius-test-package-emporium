@access @access-security
Feature: Access security — access management stays with the built-in Administrator role
  As the platform's security owner
  I want access.manage out of every custom role and every access write closed to the other roles
  So that nobody below Administrator can grant themselves more, and no request smuggles fields past the API

  Operator Q2: access.manage (read and write) is never part of a custom role. Operator Q5: a token with a secret
  scope expires within 365 days. Every role, grant and token created here is removed or revoked at the end.

  Background:
    Given the channel is the primary channel
    And a run-unique suffix is saved as "saved.run"

  Scenario Outline: AM-01 <caller> cannot create a custom role with access.manage:<level>
    Given the role "bdd-sec-{saved.run}" is deleted when the scenario ends
    And the caller is <caller>
    When the caller sends POST to "api/access/v2/admin/roles/" with body
      """
      {"key": "bdd-sec-{saved.run}", "name": "BDD security {saved.run}", "permissions": ["access.manage:<level>"]}
      """
    Then the answer is 400 with "-"
    And the answer names the issue "ACCESS_MANAGE_RESERVED"
    And the role "bdd-sec-{saved.run}" does not exist

    Examples: access managers
      | caller      | level |
      | accessadmin | write |
      | accessadmin | read  |
      | admin       | write |
      | admin       | read  |

  Scenario Outline: AM-02 <caller> cannot add access.manage to an existing custom role
    Given the role "ops-{saved.run}" is deleted when the scenario ends
    And the caller is <caller>
    When the caller sends POST to "api/access/v2/admin/roles/" with body
      """
      {"key": "ops-{saved.run}", "name": "Ops {saved.run}", "permissions": ["faq.faq:write"]}
      """
    Then the answer is 201 with "-"
    And I save the response field "id" as "saved.role"
    Given I save the newest audit entry id as "saved.mark"
    When the caller sends PATCH to "api/access/v2/admin/roles/{saved.role}/" with body
      """
      {"permissions": ["faq.faq:write", "access.manage:read"]}
      """
    Then the answer is 400 with "-"
    And the answer names the issue "ACCESS_MANAGE_RESERVED"
    And the role "saved.role" holds exactly the permissions {"faq.faq": "write"}
    And the audit log counts 0 "role.update" after "saved.mark" for target "{saved.role}"

    Examples: access managers
      | caller      |
      | accessadmin |
      | admin       |

  Scenario: AM-03 the catalogue offers access.manage as not assignable
    Given the caller is accessadmin
    When the caller sends GET to "api/access/v2/admin/catalogue/"
    Then the answer is 200 with "-"
    And the catalogue area "access.manage" is not assignable

  Scenario Outline: AM-04 <caller> is refused on every access write — <write>
    Given the role "bdd-sec-{saved.run}" is deleted when the scenario ends
    And the caller is <caller>
    And I save the caller's own user id as "saved.me"
    When the caller sends POST to "<path>" with JSON <body>
    Then the gate refuses with issue "ACCESS_DENIED"
    And the refusal names "access.manage:write"

    Examples: roles below Administrator
      | caller  | write                       | path                              | body                                             |
      | manager | grant Administrator to self | api/access/v2/admin/grants/       | {"role": "administrator", "user_id": {saved.me}} |
      | manager | create a role               | api/access/v2/admin/roles/        | {"key": "bdd-sec-{saved.run}", "name": "x"}      |
      | manager | create an application       | api/access/v2/admin/applications/ | {"name": "bdd-sec-{saved.run}"}                  |
      | editor  | grant Administrator to self | api/access/v2/admin/grants/       | {"role": "administrator", "user_id": {saved.me}} |
      | editor  | create a role               | api/access/v2/admin/roles/        | {"key": "bdd-sec-{saved.run}", "name": "x"}      |
      | editor  | create an application       | api/access/v2/admin/applications/ | {"name": "bdd-sec-{saved.run}"}                  |
      | viewer  | grant Administrator to self | api/access/v2/admin/grants/       | {"role": "administrator", "user_id": {saved.me}} |
      | viewer  | create a role               | api/access/v2/admin/roles/        | {"key": "bdd-sec-{saved.run}", "name": "x"}      |
      | viewer  | create an application       | api/access/v2/admin/applications/ | {"name": "bdd-sec-{saved.run}"}                  |
      | norole  | grant Administrator to self | api/access/v2/admin/grants/       | {"role": "administrator", "user_id": {saved.me}} |
      | norole  | create a role               | api/access/v2/admin/roles/        | {"key": "bdd-sec-{saved.run}", "name": "x"}      |
      | norole  | create an application       | api/access/v2/admin/applications/ | {"name": "bdd-sec-{saved.run}"}                  |

  Scenario: AM-05 accessadmin grants a custom role to the viewer, then revokes it and deletes the role
    Given the role "ops-{saved.run}" is deleted when the scenario ends
    And I save the id of the viewer staff user as "saved.viewer"
    And the caller is accessadmin
    When the caller sends POST to "api/access/v2/admin/roles/" with body
      """
      {"key": "ops-{saved.run}", "name": "Ops {saved.run}", "permissions": ["faq.faq:write"]}
      """
    Then the answer is 201 with "-"
    And I save the response field "id" as "saved.role"
    When the caller sends POST to "api/access/v2/admin/grants/" with body
      """
      {"role": "ops-{saved.run}", "user_id": {saved.viewer}}
      """
    Then the answer is 201 with "-"
    And I save the response field "id" as "saved.grant"
    When the caller sends DELETE to "api/access/v2/admin/grants/{saved.grant}/"
    Then the answer is 204 with "-"
    When the caller sends DELETE to "api/access/v2/admin/roles/{saved.role}/"
    Then the answer is 204 with "-"

  Scenario Outline: AM-06 mass assignment on role create is refused — <attempt>
    Given the role "bdd-sec-{saved.run}" is deleted when the scenario ends
    And the caller is accessadmin
    When the caller sends POST to "api/access/v2/admin/roles/" with JSON <body>
    Then the answer is <status> with "-"

    Examples: role bodies
      | attempt       | body                                                                             | status |
      | builtin flag  | {"key": "bdd-sec-{saved.run}", "name": "x", "permissions": [], "builtin": true}  | 400    |
      | unknown field | {"key": "bdd-sec-{saved.run}", "name": "x", "permissions": [], "bdd_unknown": 1} | 400    |
      | built-in key  | {"key": "administrator", "name": "x", "permissions": []}                         | 409    |

  Scenario Outline: AM-07 mass assignment on token create is refused — <attempt>
    Given the shared security application is saved as "saved.app"
    And the caller is accessadmin
    When the caller sends POST to "api/access/v2/admin/applications/{saved.app}/tokens/" with JSON <body>
    Then the answer is 400 with "-"

    Examples: token bodies
      | attempt                       | body                                                                                                  |
      | key_hash                      | {"name": "x", "scopes": ["checkout.storefront"], "key_hash": "0000"}                                  |
      | legacy flag                   | {"name": "x", "scopes": ["checkout.storefront"], "legacy": true}                                      |
      | revoked_at                    | {"name": "x", "scopes": ["checkout.storefront"], "revoked_at": "{days_ahead:1}"}                      |
      | publishable and secret scopes | {"name": "x", "scopes": ["checkout.storefront", "reviews.moderate"], "expires_at": "{days_ahead:30}"} |

  Scenario Outline: AM-08 a secret token expires within 365 days — <expiry>
    Given the shared security application is saved as "saved.app"
    And the caller is accessadmin
    When the caller sends POST to "api/access/v2/admin/applications/{saved.app}/tokens/" with JSON <body>
    Then the answer is <status> with "-"
    And the answer names the issue "<issue>"

    Examples: reviews.moderate tokens
      | expiry   | body                                                                            | status | issue           |
      | none     | {"name": "x", "scopes": ["reviews.moderate"]}                                   | 400    | EXPIRY_REQUIRED |
      | 366 days | {"name": "x", "scopes": ["reviews.moderate"], "expires_at": "{days_ahead:366}"} | 400    | EXPIRY_TOO_LONG |
      | 365 days | {"name": "x", "scopes": ["reviews.moderate"], "expires_at": "{days_ahead:365}"} | 201    | -               |

  Scenario: AM-09 a customer id looks exactly like an id that does not exist, and cannot receive a grant
    Given the caller is customer
    And I save the caller's own user id as "saved.customer"
    And the caller is accessadmin
    When the caller sends GET to "api/access/v2/admin/staff/{saved.customer}/"
    Then the answer is 404 with "-"
    And I keep the answer as "customer"
    When the caller sends GET to "api/access/v2/admin/staff/999999999/"
    Then I keep the answer as "nobody"
    And every answer is the same 404
    When the caller sends POST to "api/access/v2/admin/grants/" with body
      """
      {"role": "viewer", "user_id": {saved.customer}}
      """
    Then the answer is 400 with "-"

  Scenario: AM-10 me tells a customer nothing about the gate
    Given the caller is customer
    When the caller sends GET to "api/access/v2/me/"
    Then the answer is 200 with "-"
    And the response field "gate_mode" should be null
