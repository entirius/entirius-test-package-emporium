@communicator @outbound-q3 @outbound-q4 @outbound-q6
Feature: Outbound sender routes, one approval inbox and one-click unsubscribe
  As a sales operator
  I want mail to leave from the right mailbox with the colleague's other mailbox in copy, every draft in one inbox, and
  a recipient to be able to unsubscribe with one click
  So that outreach stays reachable, reviewable in bulk and compliant

  Roadmap Q3, Q4, Q6 and the code part of Q8 (entirius-infra/outbound/roadmap.md, work/q3-q4-q6-communicator.md).
  Needs the communicator branch with migration 0015 mounted in the stack; run with `make bdd TAGS=@outbound-q3`,
  `@outbound-q4` or `@outbound-q6`. Every scenario creates its own routes, drafts and recipients, and puts back what it
  changed (channel mode, default route, routes). The unsubscribe-link scenarios need
  `COMMUNICATOR_UNSUBSCRIBE_BASE_URL` set in the stack settings; without it they skip themselves.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "dry_run" mode
    And the beat has drained every due message
    And the sandbox mailbox is empty

  @outbound-q3
  Scenario: Q3 a sender route is created, listed, made the channel default and protected while it is the default
    Given the sender route "bdd-q3-a" exists from "bdd-q3-a@ecom.example.test" with copy to "bdd-q3-a@entirius.example.test"
    Then the sender routes list holds "bdd-q3-a" with copy to "bdd-q3-a@entirius.example.test"
    And creating the sender route "bdd-q3-a" again is refused with status 409
    When I make "bdd-q3-a" the default route of the channel
    Then the channel default route is "bdd-q3-a"
    And deleting the sender route "bdd-q3-a" is refused with status 409
    And making "bdd-q3-ghost" the default route of the channel is refused with status 409

  @outbound-q3
  Scenario: Q3 mail leaves from the route mailbox and the colleague's mailbox is only copied outside the sandbox
    Given the sender route "bdd-q3-b" exists from "bdd-q3-b@ecom.example.test" with copy to "bdd-q3-b@entirius.example.test"
    And the communicator channel is in "sandbox" mode
    When I create a routed approved "followup" message to "bdd-q3-b@example-shop-1.test" on the sender route "bdd-q3-b" as "saved.q3b"
    And the beat send task has run
    Then the outbound message "saved.q3b" has status "sent"
    And the sandbox message to "bdd-q3-b@example-shop-1.test" is from "bdd-q3-b@ecom.example.test"
    And the sandbox message to "bdd-q3-b@example-shop-1.test" has the header "X-Original-Cc" equal to "bdd-q3-b@entirius.example.test"
    And the sandbox message to "bdd-q3-b@example-shop-1.test" has no Cc

  @outbound-q3
  Scenario: Q3 a message naming an unknown route does not leave and says why
    Given the communicator channel is in "sandbox" mode
    When I create a routed approved "followup" message to "bdd-q3-c@example-shop-1.test" on the sender route "bdd-q3-ghost" as "saved.q3c"
    And the beat send task has run
    Then the outbound message "saved.q3c" has status "failed"
    And the outbound message "saved.q3c" has failure code "sender_route" mentioning "bdd-q3-ghost"
    And the sandbox mailbox holds 0 messages to "bdd-q3-c@example-shop-1.test"

  @outbound-q3
  Scenario: Q8 a mailbox with a daily cap of one sends one message and leaves the next one waiting
    Given the sender route "bdd-q3-cap" exists with its own fresh mailbox and a daily cap of 1
    And the communicator channel is in "sandbox" mode
    When I create a routed approved "followup" message to "bdd-q3-d1@example-shop-1.test" on the sender route "bdd-q3-cap" as "saved.q3d1"
    And I create a routed approved "followup" message to "bdd-q3-d2@example-shop-1.test" on the sender route "bdd-q3-cap" as "saved.q3d2"
    And the beat send task has run
    Then the outbound message "saved.q3d1" has status "sent"
    And the outbound message "saved.q3d2" has status "approved"
    And the sandbox mailbox holds 0 messages to "bdd-q3-d2@example-shop-1.test"

  @outbound-q3
  Scenario: Q8 a warm-up route starts at its first-day cap and the policy shows the cap of today
    Given the sender route "bdd-q3-warm" exists with a warm-up from 5 a day by 2 up to 30
    Then the sender route "bdd-q3-warm" has a cap of 5 today and a warm-up start date
    And the send policy lists the mailbox of "bdd-q3-warm" with a cap of 5 today

  @outbound-q4
  Scenario: Q4 drafts of different routes wait in one inbox that filters by route and shows the reason they would be refused
    Given the sender route "bdd-q4-a" exists from "bdd-q4-a@ecom.example.test" with copy to "bdd-q4-a@entirius.example.test"
    When I create a draft for review to "bdd-q4-1@example-shop-1.test" on the sender route "bdd-q4-a" as "saved.q4a"
    And I create a draft for review to "bdd-q4-2@example-shop-1.test" on the sender route "bdd-q4-ghost" as "saved.q4b"
    Then the approval inbox of this run holds 2 drafts
    And the approval inbox of this run on the route "bdd-q4-a" holds 1 drafts
    And the approval inbox row of "saved.q4a" is from "bdd-q4-a@ecom.example.test" with template "reply.thanks" and no blocker
    And the approval inbox row of "saved.q4b" has a blocker mentioning "bdd-q4-ghost"

  @outbound-q4
  Scenario: Q4 a bulk approve and a bulk reject change the drafts, name what failed and are logged with the user
    Given the sender route "bdd-q4-b" exists from "bdd-q4-b@ecom.example.test" with copy to "bdd-q4-b@entirius.example.test"
    When I create a draft for review to "bdd-q4-3@example-shop-1.test" on the sender route "bdd-q4-b" as "saved.q4c"
    And I create a draft for review to "bdd-q4-4@example-shop-1.test" on the sender route "bdd-q4-b" as "saved.q4d"
    And I create a draft for review to "bdd-q4-5@example-shop-1.test" on the sender route "bdd-q4-ghost" as "saved.q4e"
    And I bulk approve the drafts "saved.q4c, saved.q4e"
    Then the bulk result lists "saved.q4c" as done and "saved.q4e" as failed
    And the review message "saved.q4c" has status "approved"
    When I bulk reject the drafts "saved.q4d" with the reason "bdd reject"
    Then the review message "saved.q4d" has status "rejected"
    And the bulk approval log has an entry of the admin user for each of the two batches

  @outbound-q4
  Scenario: Q4 a bulk request above the size limit is refused and changes nothing
    When I bulk approve 101 draft ids
    Then the last response status is 400

  @outbound-q6
  Scenario: Q6 a forged unsubscribe token is refused and nobody is suppressed
    When the unsubscribe link "not-a-real-token" is posted
    Then the last response status is 400
    When the unsubscribe link "not-a-real-token" is opened
    Then the last response status is 404

  @outbound-q6
  Scenario: Q6 a mail carries the one-click headers and posting the link suppresses the address
    Given the communicator channel is in "sandbox" mode
    When I create an approved "followup" message to "bdd-q6-a@example-shop-1.test" as "saved.q6a"
    And the beat send task has run
    Then the sandbox message to "bdd-q6-a@example-shop-1.test" has the one-click unsubscribe headers
    When the unsubscribe link of the sandbox message to "bdd-q6-a@example-shop-1.test" is opened
    Then the last response status is 200
    And "bdd-q6-a@example-shop-1.test" is not suppressed yet
    When the unsubscribe link of the sandbox message to "bdd-q6-a@example-shop-1.test" is posted as a one-click request
    Then the last response status is 200
    And "bdd-q6-a@example-shop-1.test" is suppressed on the channel
    When I create a "followup" message to "bdd-q6-a@example-shop-1.test" as "saved.q6b" after the unsubscribe
    And the beat send task has run
    Then the outbound message "saved.q6b" has status "suppressed"

  @outbound-q6
  Scenario: Q6 a message for a template that requires the legal footer is not created without one
    When I try to create a "followup" message to "bdd-q6-b@example-shop-1.test" without a legal footer
    Then the last response status is 400
