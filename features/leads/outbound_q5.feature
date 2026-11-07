@leads @outbound-q3l @outbound-q5 @outbound-q7
Feature: Outbound — sender route, address verification and the do-not-contact list
  As a sales operator
  I want a file to go out through one mailbox route, bad addresses to be caught before sending
  and an opt-out to stop the person everywhere
  So that outreach stays deliverable and compliant

  Roadmap Q3/Q5/Q7 (entirius-infra/outbound/roadmap.md, section 9). Needs the leads build with migration 0013. Every
  scenario imports its own company, so none consumes the seed. Tags: outbound-q3l is the leads side of sender routes,
  outbound-q5 verification, outbound-q7 compliance. No DNS is used: the invalid address is a disposable domain.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  @outbound-q3l
  Scenario: Q3 a whole file imported through a route puts the route on its companies
    Given a fresh company is imported through the sender route "ecomhouse" as "company_id"
    Then the company "company_id" has the sender route "ecomhouse"

  @outbound-q3l
  Scenario: Q3 the route of chosen companies changes in bulk
    Given a fresh company is imported through the sender route "ecomhouse" as "company_id"
    When the sender route of the company "company_id" is changed to "entirius" in bulk
    Then the company "company_id" has the sender route "entirius"

  @outbound-q5
  Scenario: Q5 a disposable address is invalid, listed, and blocks the send
    Given a fresh company is imported as "company_id"
    And the contact of the company "company_id" gets the address "buyer@mailinator.com"
    When the address of the contact of the company "company_id" is verified
    Then the verification status is "invalid" with the reason "disposable"
    And the invalid addresses list contains the contact of the company "company_id"
    And the send check of the contact of the company "company_id" refuses with "email_invalid"

  @outbound-q7
  Scenario: Q7 a contact with a legal basis is mailable and the report says why
    Given a fresh company is imported as "company_id"
    Then the send check of the first contact of the company "company_id" allows outreach and names the legal basis

  @outbound-q7
  Scenario: Q7 an opt-out on the shared list stops the contact
    Given a fresh company is imported as "company_id"
    When the email of the first contact of the company "company_id" is put on the do-not-contact list
    Then the send check of the first contact of the company "company_id" refuses with "opted_out"
    And drafting a mail to the company "company_id" is refused by the outreach gate
