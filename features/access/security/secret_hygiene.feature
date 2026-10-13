@access @access-security
Feature: Access security — a token secret shows once and nowhere else
  As the platform's security owner
  I want the raw token value only in the create and rotate answers, never cached and never echoed later
  So that a secret cannot be read back from any list, detail or audit page

  The checks look for the `raw` and `key_hash` keys anywhere in the JSON and for every raw value this scenario holds
  anywhere in the body. Token-abuse refusals get the same check (`token_abuse.feature`).

  Background:
    Given the shared security application is saved as "saved.app"
    And the caller is accessadmin

  Scenario Outline: SH-01 after a token create, <page> carries no secret
    When the caller sends POST to "api/access/v2/admin/applications/{saved.app}/tokens/" with body
      """
      {"name": "bdd-security hygiene", "scopes": ["contact_forms.submit"], "expires_at": "{days_ahead:30}"}
      """
    Then the answer is 201 with "-"
    And the answer was a one-time secret marked no-store
    When the caller sends GET to "<path>"
    Then the answer is 200 with "-"
    And the answer carries no token secret

    Examples: access admin pages
      | page                   | path                                                               |
      | the applications list  | api/access/v2/admin/applications/?page_size=100                    |
      | the application detail | api/access/v2/admin/applications/{saved.app}/                      |
      | the token list         | api/access/v2/admin/applications/{saved.app}/tokens/?page_size=100 |
      | the audit list         | api/access/v2/admin/audit/?page_size=100                           |

  Scenario: SH-02 a rotation shows the new secret once and the token list neither
    When the caller sends POST to "api/access/v2/admin/applications/{saved.app}/tokens/" with body
      """
      {"name": "bdd-security rotation", "scopes": ["reviews.moderate"], "expires_at": "{days_ahead:30}"}
      """
    Then the answer is 201 with "-"
    And I save the response field "id" as "saved.token"
    When the caller sends POST to "api/access/v2/admin/tokens/{saved.token}/rotate/" with body
      """
      {"overlap_hours": 0}
      """
    Then the answer is 201 with "-"
    And the answer was a one-time secret marked no-store
    When the caller sends GET to "api/access/v2/admin/applications/{saved.app}/tokens/?page_size=100"
    Then the answer is 200 with "-"
    And the answer carries no token secret
