@checkout @order-flow @v2
Feature: Checkout API v2 -- Cart to Order
  As a guest customer
  I want to complete checkout from cart to order
  So that I can buy products at the Emporium

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  Scenario: Guest completes checkout from cart to order
    Given I create a v2 cart with product "ENT-C003" quantity 1 in currency "EUR"
    And the v2 cart addresses are set to country "DE"
    When I GET the v2 shipping methods for the cart
    Then the response status should be 200
    And the v2 shipping methods list should not be empty
    When I select the v2 shipping method "europe-standard"
    And I select the v2 payment method "banktransfer"
    Then the v2 cart validation status should be "valid"
    When I create an order from the v2 cart
    Then the response status should be 201
    And the order should have status "unpaid" and a pretty id

  Scenario: Every checkout country of the channel offers a shipping method
    Then every v2 checkout country has at least one shipping method in currency "EUR"
