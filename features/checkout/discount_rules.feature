@checkout @discount-rules @import-verification
Feature: Checkout API -- Discount Rules
  As a customer
  I want to apply discount codes to my cart
  So that I can receive discounts on my purchases

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  # ─────────────────────────────────────────────────────────────────────
  # Import Verification
  # ─────────────────────────────────────────────────────────────────────

  Scenario: Discount rules CSV exists and contains expected test rules
    When the CSV discount rules are loaded
    Then the discount rules count should be 10
    And the discount rules should contain rule with name "TEST_PERCENT_10"
    And the discount rules should contain rule with name "TEST_PRICE_50"
    And the discount rules should contain rule with name "TEST_CHEAPEST_GRATIS"
    And the discount rules should contain rule with name "TEST_MOST_EXPENSIVE_GRATIS"
    And the discount rules should contain rule with name "TEST_FREE_SHIPPING"
    And the discount rules should contain rule with name "TEST_STEP_PRICE_PERCENT"
    And the discount rules should contain rule with name "TEST_GRATIS_STEPPED"
    And the discount rules should contain rule with name "TEST_AUTO_APPLY"
    And the discount rules should contain rule with name "TEST_FIRST_ORDER_LOGGED"
    And the discount rules should contain rule with name "TEST_COMBINABLE"

  # ─────────────────────────────────────────────────────────────────────
  # Simple Percent Discount (10%)
  # ─────────────────────────────────────────────────────────────────────

  Scenario: Apply 10% discount code to cart
    Given I have an empty cart
    And I add product "ENT-S001" with quantity 1 to cart
    When I apply discount code "PERCENT10"
    Then the discount should be applied successfully
    And the discount type should be "percent_discount"
    And the discount value should be 10 percent

  Scenario: 10% discount code works with minimum order amount of 0
    Given I have an empty cart
    And I add product "ENT-C001" with quantity 1 to cart
    When I apply discount code "PERCENT10"
    Then the discount should be applied successfully

  # ─────────────────────────────────────────────────────────────────────
  # Price Discount (50 PLN at min 200 PLN)
  # ─────────────────────────────────────────────────────────────────────

  Scenario: Apply 50 PLN discount code when cart meets minimum
    Given I have an empty cart
    And I add products totaling at least 200 PLN
    When I apply discount code "PRICE50"
    Then the discount should be applied successfully
    And the discount type should be "price_discount"
    And the discount amount should be 50 EUR

  # ─────────────────────────────────────────────────────────────────────
  # Gratis Rules (Cheapest / Most Expensive)
  # ─────────────────────────────────────────────────────────────────────

  Scenario: Apply cheapest product gratis at min 300 PLN
    Given I have an empty cart
    And I add products totaling at least 300 PLN
    When I apply discount code "CHEAPEST_FREE"
    Then the discount should be applied successfully
    And the discount type should be "cheapest_gratis"

  Scenario: Apply most expensive product gratis at min 1000 PLN
    Given I have an empty cart
    And I add products totaling at least 1000 PLN
    When I apply discount code "EXPENSIVE_FREE"
    Then the discount should be applied successfully
    And the discount type should be "most_expensive_gratis"

  # ─────────────────────────────────────────────────────────────────────
  # Progressive Discounts (Step Price Percent)
  # ─────────────────────────────────────────────────────────────────────

  Scenario: Progressive discount at 500 PLN gives 10%
    Given I have an empty cart
    And I add products totaling at least 500 PLN
    When I apply discount code "STEP_PRICE_PCT"
    Then the discount should be applied successfully
    And the discount value should be 10 percent

  Scenario: Progressive discount at 1000 PLN gives 15%
    Given I have an empty cart
    And I add products totaling at least 1000 PLN
    When I apply discount code "STEP_PRICE_PCT"
    Then the discount should be applied successfully
    And the discount value should be 15 percent

  Scenario: Progressive discount at 2000 PLN gives 20%
    Given I have an empty cart
    And I add products totaling at least 2000 PLN
    When I apply discount code "STEP_PRICE_PCT"
    Then the discount should be applied successfully
    And the discount value should be 20 percent

  # ─────────────────────────────────────────────────────────────────────
  # Progressive Gratis (Gratis Stepped)
  # TODO: Requires DiscountModeOfAction fixture records to define eligible
  #       products for gratis selection. Re-enable when fixture is ready.
  # ─────────────────────────────────────────────────────────────────────

  # Scenario: Progressive gratis at 300 PLN gives 1 item
  #   Given I have an empty cart
  #   And I add products totaling at least 300 PLN
  #   When I apply discount code "GRATIS_STEP"
  #   Then 1 gratis products should be available

  # Scenario: Progressive gratis at 1000 PLN gives 3 items
  #   Given I have an empty cart
  #   And I add products totaling at least 1000 PLN
  #   When I apply discount code "GRATIS_STEP"
  #   Then 3 gratis products should be available


