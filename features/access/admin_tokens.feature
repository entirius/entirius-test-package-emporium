@access @access-admin-tokens @v2 @module-pim
Feature: Application tokens on admin routes
  As an integrator
  I want my application key to buy a short-lived admin JWT limited to the key's areas
  So that an integration creates products without a person's password and stops the moment its key is revoked

  Background:
    Given the channel is the first seed channel

  Scenario: AT-01 an exchanged key reads the areas it holds
    Given an application "saved.app" for this run
    And a token "saved.erp" of application "saved.app" with scopes "pim.products:write, pim.schema:read"
    When I exchange the token "saved.erp"
    Then the response status should be 200
    And the exchange answer is a Bearer JWT valid for 300 seconds
    When I send GET to "pim/admin/{channel_idx}/products/" with the exchanged JWT of "saved.erp"
    Then the response status should be 200
    When I send GET to "pim/admin/features/" with the exchanged JWT of "saved.erp"
    Then the response status should be 200

  Scenario: AT-02 a write without the write scope is refused by the gate
    Given an application "saved.app" for this run
    And a token "saved.reader" of application "saved.app" with scopes "pim.products:read"
    When I exchange the token "saved.reader"
    And I send POST to "pim/admin/{channel_idx}/products/" with the exchanged JWT of "saved.reader"
    Then the gate refuses with issue "ACCESS_DENIED"
    And the refusal names "pim.products:write"
    When I send GET to "pim/admin/features/" with the exchanged JWT of "saved.reader"
    Then the gate refuses with issue "ACCESS_DENIED"

  Scenario: AT-03 a revoked key stops its JWT on the next request, inside the JWT's lifetime
    Given an application "saved.app" for this run
    And a token "saved.erp" of application "saved.app" with scopes "pim.products:read"
    When I exchange the token "saved.erp"
    And I send GET to "pim/admin/{channel_idx}/products/" with the exchanged JWT of "saved.erp"
    Then the response status should be 200
    When I revoke the token "saved.erp"
    And I send GET to "pim/admin/{channel_idx}/products/" with the exchanged JWT of "saved.erp"
    Then the gate refuses with issue "TOKEN_INACTIVE"
    When I exchange the token "saved.erp"
    Then the response status should be 401

  Scenario: AT-04 publishable and admin scopes never share a token
    Given an application "saved.app" for this run
    When I issue a token of application "saved.app" with scopes "checkout.storefront, pim.products:read"
    Then the response status should be 400

  Scenario: AT-05 a key without an admin scope buys nothing
    Given an application "saved.app" for this run
    And a token "saved.vault" of application "saved.app" with scopes "vault.api"
    When I exchange the token "saved.vault"
    Then the response status should be 401

  Scenario: AT-06 the service account cannot sign in with a password
    Given an application "saved.app" for this run
    And a token "saved.erp" of application "saved.app" with scopes "pim.products:read"
    When the service account of application "saved.app" signs in with the password "access-app"
    Then the response status should be 401
    And the service account of application "saved.app" is not in the staff list

  Scenario: AT-07 a token never manages access
    Given an application "saved.app" for this run
    When I issue a token of application "saved.app" with scopes "access.manage:read"
    Then the response status should be 400
