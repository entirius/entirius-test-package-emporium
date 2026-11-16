@checkout @order-mail @module-email @v2
Feature: Checkout -- order confirmation and cancellation e-mails
  As a buyer at the Emporium
  I want an e-mail when my order is placed and when it is canceled
  So that I know what I bought, how to pay and what happened to it

  Real mail: the worker sends through GreenMail (zeno: make mail) and the steps read the buyer's own mailbox.
  Every scenario empties the mailbox and places its own order, so the feature re-runs on one database.
  SKUs are ones with a large stock (package/qty.csv); method codes come from fixtures/django_checkout.cfg.yaml.

  Background:
    Given the sandbox mailbox is empty

  Scenario: A bank transfer order gets one confirmation with the items, the total and the transfer details
    Given the buyer places an order of "ENT-O001" shipped by "europe-standard" paid by "banktransfer"
    Then the buyer receives 1 order e-mails
    And the newest order e-mail subject is "Order {number} — confirmation"
    And the newest order e-mail names every ordered item
    And the newest order e-mail text contains "Total: {total}"
    And the newest order e-mail text contains "Transfer title: {number}"
    And the newest order e-mail text contains "Account: PL00 0000 0000 0000 0000 0000 0001"

  Scenario: A cash on delivery order gets a confirmation with the amount due on delivery
    Given the buyer places an order of "ENT-O001" shipped by "europe-cod" paid by "cod"
    Then the buyer receives 1 order e-mails
    And the newest order e-mail text contains "You will pay on delivery: {total}"

  Scenario: An order to a pickup point names the point
    Given the buyer places an order of "ENT-O001" shipped by "europe-pickup" paid by "banktransfer" to the pickup point "BDD Pickup Dock 7"
    Then the buyer receives 1 order e-mails
    And the newest order e-mail text contains "Pickup point: BDD Pickup Dock 7"

  Scenario: An order placed in English gets an English subject
    Given the buyer places an order of "ENT-O001" shipped by "europe-standard" paid by "banktransfer" in language "en"
    Then the buyer receives 1 order e-mails
    And the newest order e-mail subject is "Order {number} — confirmation"

  Scenario: An order placed in Polish gets a Polish confirmation
    Given the buyer places an order of "ENT-O001" shipped by "europe-standard" paid by "banktransfer" in language "pl"
    Then the buyer receives 1 order e-mails
    And the newest order e-mail subject is "Zamówienie {number} — potwierdzenie"
    And the newest order e-mail names every ordered item

  Scenario: An online payment left unpaid sends nothing
    Given the buyer places an order of "ENT-O001" shipped by "europe-standard" paid by "online-card"
    Then the buyer receives no order e-mail

  Scenario: An online payment confirmed by an admin gets one confirmation, however often it is confirmed
    Given the buyer places an order of "ENT-O001" shipped by "europe-standard" paid by "online-card"
    When an admin sets the order status to "confirmed"
    Then the order's "confirmation" e-mail was sent 1 times
    When an admin sets the order status to "confirmed" again
    Then the order's "confirmation" e-mail was sent 1 times
    And the buyer receives 1 order e-mails

  Scenario: An admin resends the confirmation
    Given the buyer places an order of "ENT-O001" shipped by "europe-standard" paid by "banktransfer"
    And the order's "confirmation" e-mail was sent 1 times
    When an admin resends the order's "confirmation" e-mail
    Then the order's "confirmation" e-mail was sent 2 times
    And the buyer receives 2 order e-mails

  Scenario: The confirmation has a text part and an HTML part
    Given the buyer places an order of "ENT-O001" shipped by "europe-standard" paid by "banktransfer"
    Then the buyer receives 1 order e-mails
    And the newest order e-mail has a text and an HTML part

  Scenario: A confirmed transfer order canceled by an admin gets one cancellation
    Given the buyer places an order of "ENT-O001" shipped by "europe-standard" paid by "banktransfer"
    And the order's "confirmation" e-mail was sent 1 times
    When an admin sets the order status to "confirmed"
    And an admin cancels the order
    Then the order's "canceled" e-mail was sent 1 times
    And the buyer receives 2 order e-mails
    And the newest order e-mail subject is "Order {number} — canceled"

  Scenario: An online payment canceled unpaid sends nothing at all
    Given the buyer places an order of "ENT-O001" shipped by "europe-standard" paid by "online-card"
    When an admin cancels the order
    Then the buyer receives no order e-mail

  Scenario: A split purchase gets one confirmation with every order number
    Given the buyer places an order of "ENT-S005,ENT-B002" shipped by "europe-standard" paid by "banktransfer"
    Then the buyer receives 1 order e-mails
    And the newest order e-mail subject is "Order {numbers} — confirmation"
    And the newest order e-mail names every ordered item
    And the newest order e-mail text contains "Total: {total}"
