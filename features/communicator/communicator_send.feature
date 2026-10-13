@communicator
Feature: Communicator — beat delivery under the channel send policy
  As the sales team
  I want approved messages to leave only through the beat, inside the channel policy and mode
  So that nothing reaches a real inbox by accident and the daily cap holds

  Data: fixtures/django_communicator.cfg.yaml (channel in sandbox mode to sandbox@greenmail.test; send
  policy business days 08:00-17:00 in the channel timezone, cap 10, spread off; sequence followup at
  3/5/7 days over six pool texts). The channel clock and both beat tasks run through the development
  endpoints test/clock/ and test/send-due/. The Background drains every due message in dry_run, so mail
  from earlier scenarios never lands here; every scenario writes to its own fresh thread and counts only
  the sandbox mail addressed to its own recipient (X-Original-To). Channel clock days are a fixed holiday-free
  reference week (2026-09-21), and the Background clears that week's send counters, so the feature passes on
  any calendar date and on re-runs. The cap scenario raises the cap by what the counter already holds for its
  day; the policy is restored afterwards.

  Background:
    Given I am authenticated as an admin user
    And the channel is the primary channel
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "dry_run" mode
    And the beat has drained every due message
    And the sandbox mailbox is empty

  Scenario: C-13 a dry_run channel records would_send and sends nothing
    When I create an approved "followup" message to "bdd-c13@example-shop-1.test" as "saved.c13"
    And the beat send task has run
    Then the outbound message "saved.c13" has status "would_send"
    And the sandbox mailbox holds 0 messages to "bdd-c13@example-shop-1.test"

  Scenario: C-14 a sandbox channel redirects to the sandbox mailbox with the original recipient
    Given the communicator channel is in "sandbox" mode
    When I create an approved "followup" message to "bdd-c14@example-shop-1.test" as "saved.c14"
    And the beat send task has run
    Then the outbound message "saved.c14" has status "sent"
    And the sandbox mailbox holds 1 messages to "bdd-c14@example-shop-1.test"
    And the sandbox message to "bdd-c14@example-shop-1.test" has a subject starting with "[SANDBOX] "
    And the sandbox message to "bdd-c14@example-shop-1.test" is multipart/alternative with our Message-ID

  Scenario: C-16 nothing leaves on a weekend and the next slot is visible
    Given the communicator channel is in "sandbox" mode
    And the channel clock is saturday 10:00
    When I create an approved "followup" message to "bdd-c16@example-shop-1.test" as "saved.c16"
    And the beat send task has run
    Then the sandbox mailbox holds 0 messages to "bdd-c16@example-shop-1.test"
    And the outbound message "saved.c16" has status "approved"
    And the outbound message "saved.c16" has its next slot on monday at 08:00

  Scenario: C-28 a follow-up goes into the same thread with References to the first mail
    Given the communicator channel is in "sandbox" mode
    When I create an approved "followup" message to "bdd-c28@example-shop-1.test" as "saved.c28"
    And the beat send task has run
    Then the sandbox mailbox holds 1 messages to "bdd-c28@example-shop-1.test"
    When I start the "followup" sequence in the thread of "saved.c28"
    And the channel clock moves 3 days forward
    And the beat send task has run
    Then the response field "follow_ups_scheduled" should equal integer 1
    And the sandbox mailbox holds 2 messages to "bdd-c28@example-shop-1.test"
    And the last sandbox message to "bdd-c28@example-shop-1.test" references the first one

  @communicator-oneshot
  Scenario: C-17 the daily cap holds and the rest waits for the next day
    Given the channel clock is wednesday 10:00
    And the beat has drained every due message
    And the communicator channel is in "sandbox" mode
    And the daily cap leaves room for 10 more messages today
    When I create 11 approved "followup" messages to "bdd-c17@example-shop-1.test"
    And the beat send task has run
    Then the response field "sent" should equal integer 10
    And the response field "deferred" should equal integer 1
    And the sandbox mailbox holds 10 messages to "bdd-c17@example-shop-1.test"
