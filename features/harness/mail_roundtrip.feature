@harness
Feature: Harness — mail sandbox round trip
  As a developer of the leads platform
  I want every mail of the stack to land in a sandbox the suite can read and write
  So that sending and inbound scenarios assert real SMTP/IMAP traffic instead of mocks

  Needs the GreenMail container (zeno: make mail). Uses only entirius_tests.mail — no module, no API.

  Background:
    Given the sandbox mailbox is empty

  Scenario: A mail sent over SMTP is visible through the REST API
    When I send the fixture mail "reply_plain.eml" over SMTP to the sandbox
    Then the sandbox mailbox contains 1 messages
    And the last sandbox message subject starts with "Re: Your shop audit"

  Scenario: An injected reply carries the rewritten In-Reply-To
    Given the value "<bdd-outbound-1@greenmail.test>" is saved as "saved.outbound_message_id"
    When I inject the fixture mail "reply_plain.eml" into INBOX replying to "saved.outbound_message_id"
    Then the sandbox mailbox contains 1 messages
    And the last sandbox message has header "In-Reply-To" equal to "{saved.outbound_message_id}"
