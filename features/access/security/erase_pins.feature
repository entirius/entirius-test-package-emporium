@access @access-security
Feature: Access security — a channel-pinned erase token erases only in its channel
  As the platform's security owner
  I want a GDPR erase token pinned to one shop to find nobody of another shop
  So that a leaked key of shop A cannot delete shop B's customers (D3)

  The customer is a run-unique staff account (its Customer row comes from FIX-12) moved to the second seed channel
  through the superuser's Django admin — the storefront signup is not available on zeno. The scenario ends by erasing
  it. Checkout erase in the pinned channel is covered by the checkout module tests (FIX-12): the checkout steps place
  orders with one fixed guest e-mail on every channel, so no e-mail lives on the second channel only.

  Background:
    Given a run-unique suffix is saved as "saved.run"
    And the caller is accessadmin
    When the caller sends POST to "api/access/v2/admin/staff/" with body
      """
      {"username": "bdd-erase-{saved.run}", "email": "bdd-erase-{saved.run}@example.com", "role": "viewer"}
      """
    Then the answer is 201 with "-"
    And I save the response field "id" as "saved.account"
    And the customer account of user "saved.account" belongs to the second seed channel

  Scenario: EP-01 an accounts erase token pinned to the first channel finds nobody of the second, the second's erases
    Given a security token "first" with scope "accounts.erase" pinned to the first seed channel
    And a security token "second" with scope "accounts.erase" pinned to the second seed channel
    And the channel is the first seed channel
    And the caller is anonymous
    And the caller presents the token "first" in "X-API-ADMIN-KEY"
    When the caller sends DELETE to "api-admin/accounts/v1/{channel_idx}/customer/delete" with body
      """
      {"email": "bdd-erase-{saved.run}@example.com"}
      """
    Then the answer is 404 with "-"
    And I keep the answer as "customer of the second channel"
    When the caller sends DELETE to "api-admin/accounts/v1/{channel_idx}/customer/delete" with body
      """
      {"email": "bdd-nobody-{saved.run}@example.com"}
      """
    Then I keep the answer as "unknown e-mail"
    And every answer is the same 404
    Given the channel is the second seed channel
    And the caller is anonymous
    And the caller presents the token "second" in "X-API-ADMIN-KEY"
    When the caller sends DELETE to "api-admin/accounts/v1/{channel_idx}/customer/delete" with body
      """
      {"email": "bdd-erase-{saved.run}@example.com"}
      """
    Then the answer is 200 with "-"
    And the answer field "data.deleted" is true
