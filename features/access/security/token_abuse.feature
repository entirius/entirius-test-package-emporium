@access @access-security
Feature: Access security — token abuse gets one answer, legacy keys keep working
  As the platform's security owner
  I want every way a token can be wrong to look the same from outside
  So that a caller learns nothing about which tokens exist, were revoked, expired or belong elsewhere

  Every token here is fresh (its own throttle bucket, apart from plan 17's) and expires 30 days ahead (a choice since
  D31, not a rule); the answers
  are compared without their per-request debug_id, and none of them may carry a token value.

  Background:
    Given the channel is the primary channel

  Scenario: TA-01 every token failure on the contact-form submit route answers the same
    Given an unknown token value "unknown"
    And a security token "revoked" with scope "contact_forms.submit" pinned to the first seed channel
    And a security token "rotated" with scope "contact_forms.submit" pinned to the first seed channel
    And a security token "expired" with scope "contact_forms.submit" pinned to the first seed channel that has expired
    And a security token "wrong-scope" with scope "contact_forms.booking" pinned to the first seed channel
    And a security token "other-channel" with scope "contact_forms.submit" pinned to the second seed channel
    When I revoke the token "revoked"
    And I rotate the token "rotated" without overlap as "successor"
    And the tokens "unknown, revoked, rotated, expired, wrong-scope, other-channel" are sent in "X-API-KEY" with POST to "api/contact-forms/v2/{channel_idx}/submit/"
      """
      {"email": "bdd-access-security@example.com", "body": {"name": "BDD access security"}}
      """
    Then every answer is the same 401
    And no answer carries a token secret

  Scenario: TA-02 every token failure on the reviews moderation route answers the same
    Given an unknown token value "unknown"
    And a security token "revoked" with scope "reviews.moderate"
    And a security token "rotated" with scope "reviews.moderate"
    And a security token "wrong-scope" with scope "returns.api"
    When I revoke the token "revoked"
    And I rotate the token "rotated" without overlap as "successor"
    And the tokens "unknown, revoked, rotated, wrong-scope" are sent in "X-API-KEY" with PATCH to "api/reviews/v1/{channel_idx}/reviews/00000000-0000-4000-8000-000000000000/"
      """
      {}
      """
    Then every answer is the same 401
    And no answer carries a token secret

  Scenario: TA-03 a publishable token in X-API-ADMIN-KEY does not open the erase route
    Given a security token "publishable" with scope "checkout.storefront"
    When the tokens "publishable" are sent in "X-API-ADMIN-KEY" with DELETE to "api-admin/accounts/v1/{channel_idx}/customer/delete"
    Then every answer is the same 401
    And no answer carries a token secret

  Scenario: TA-04 an erase token does not open the storefront cart
    Given a security token "erase" with scope "checkout.erase"
    When the tokens "erase" are sent in "X-API-KEY" with GET to "api/checkout/v2/{channel_idx}/countries/"
    Then every answer is the same 401
    And no answer carries a token secret

  Scenario: TA-05 a token in Authorization Bearer does not open a key route
    Given a security token "submit" with scope "contact_forms.submit" pinned to the first seed channel
    When the tokens "submit" are sent in "Authorization" with POST to "api/contact-forms/v2/{channel_idx}/submit/"
      """
      {"email": "bdd-access-security@example.com", "body": {"name": "BDD access security"}}
      """
    Then every answer is the same 401
    And no answer carries a token secret

  Scenario Outline: TA-06 a 10 KB X-API-KEY is a client error on <route>, never a 500
    Given an oversized token value "oversized" of 10240 characters
    When the tokens "oversized" are sent in "X-API-KEY" with <method> to "<path>"
    Then every answer is a client error

    Examples: key routes
      | route              | method | path                                                                       |
      | contact-form types | GET    | api/contact-forms/v2/{channel_idx}/form-types/                             |
      | storefront cart    | GET    | api/checkout/v2/{channel_idx}/countries/                                   |
      | reviews moderation | PATCH  | api/reviews/v1/{channel_idx}/reviews/00000000-0000-4000-8000-000000000000/ |

  Scenario: TA-07 the legacy checkout fixture key still opens the storefront cart and never expires by itself
    When I make a storefront checkout call on the first seed channel
    Then the application "Legacy keys: django_checkout" holds a legacy "checkout.storefront" token pinned to the first seed channel without expiry, used just now

  Scenario: TA-08 a team sets, refuses and clears an expiry on the legacy checkout token
    Given I save the id of the legacy "checkout.storefront" token of application "Legacy keys: django_checkout" pinned to the first seed channel as "saved.legacy"
    And the expiry of token "saved.legacy" is cleared when the scenario ends
    And I save the newest audit entry id as "saved.mark"
    And the caller is admin
    When the caller sends POST to "api/access/v2/admin/tokens/{saved.legacy}/expiry/" with body
      """
      {"expires_at": "{days_ahead:30}"}
      """
    Then the answer is 200 with "-"
    And the answered expiry is 30 days ahead
    And the audit log counts 1 "token.expiry" after "saved.mark" for target "{saved.legacy}"
    When I make a storefront checkout call on the first seed channel
    And the caller sends POST to "api/access/v2/admin/tokens/{saved.legacy}/expiry/" with body
      """
      {"expires_at": "{days_ahead:-1}"}
      """
    Then the answer is 400 with "-"
    And the answer names the issue "EXPIRY_IN_PAST"
    When the caller sends POST to "api/access/v2/admin/tokens/{saved.legacy}/expiry/" with body
      """
      {"expires_at": null}
      """
    Then the answer is 200 with "-"
    And the response field "expires_at" should be null

  Scenario: TA-09 an issued secret token takes any future expiry or none (D31: no lifetime cap)
    Given a security token "saved.secret" with scope "reviews.moderate"
    And the caller is admin
    When the caller sends POST to "api/access/v2/admin/tokens/{saved.secret}/expiry/" with body
      """
      {"expires_at": null}
      """
    Then the answer is 200 with "-"
    And the response field "expires_at" should be null
    When the caller sends POST to "api/access/v2/admin/tokens/{saved.secret}/expiry/" with body
      """
      {"expires_at": "{days_ahead:366}"}
      """
    Then the answer is 200 with "-"
    And the answered expiry is 366 days ahead
