@access @public @v2
Feature: Access tokens on the contact-forms key routes and legacy keys
  As a shop operator
  I want application tokens that are scoped, channel-pinned, revocable and rotatable
  So that a widget key opens exactly the routes and channel it was issued for

  Scenario: T-01 a submit token pinned to the first channel submits there only
    Given an application "saved.app" for this run
    And a token "saved.submit" of application "saved.app" with scope "contact_forms.submit" pinned to the first seed channel
    When I submit a contact form with the token "saved.submit" on the first seed channel
    Then the response status should be 201
    When I submit a contact form with the token "saved.submit" on the second seed channel
    Then the response status should be 401

  Scenario: T-02 a booking-only token cannot submit a contact form
    Given an application "saved.app" for this run
    And a token "saved.booking" of application "saved.app" with scope "contact_forms.booking"
    When I submit a contact form with the token "saved.booking" on the first seed channel
    Then the response status should be 401

  Scenario: T-03 a revoked token stops at once
    Given an application "saved.app" for this run
    And a token "saved.submit" of application "saved.app" with scope "contact_forms.submit"
    When I submit a contact form with the token "saved.submit" on the first seed channel
    Then the response status should be 201
    When I revoke the token "saved.submit"
    And I submit a contact form with the token "saved.submit" on the first seed channel
    Then the response status should be 401

  Scenario: T-04 a rotation without overlap retires the old token and keeps the pin
    Given an application "saved.app" for this run
    And a token "saved.old" of application "saved.app" with scope "contact_forms.submit" pinned to the first seed channel
    When I rotate the token "saved.old" without overlap as "saved.new"
    And I submit a contact form with the token "saved.old" on the first seed channel
    Then the response status should be 401
    When I submit a contact form with the token "saved.new" on the first seed channel
    Then the response status should be 201
    When I submit a contact form with the token "saved.new" on the second seed channel
    Then the response status should be 401

  Scenario: T-05 the checkout fixture key lives on as a legacy token that never expires by itself
    When I make a storefront checkout call on the first seed channel
    Then the application "Legacy keys: django_checkout" holds a legacy "checkout.storefront" token without expiry, used just now
