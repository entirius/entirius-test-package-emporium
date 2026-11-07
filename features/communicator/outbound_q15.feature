@communicator @outbound-q15
Feature: Outbound sending health and the pause of a sender route
  As a sales operator
  I want to see how healthy each sending mailbox is and to stop one route without stopping the whole channel
  So that a burning mailbox cannot spoil the reputation of the others

  Roadmap Q15 and Q30 (entirius-infra/outbound/roadmap.md, work/q15-q30-health.md). Needs the communicator branch with
  migration 0017 in the stack. Run with `make bdd TAGS=@outbound-q15`. The automatic pause judges live channels only, so
  it is covered by the module tests; here the numbers, the policy, the manual pause and the log run against the real API
  in the sandbox. Every scenario creates its own routes and puts the policy back.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "sandbox" mode
    And the beat has drained every due message

  Scenario: Q15 the auto-pause policy is off by default, validated and saved
    Then the health policy is off with the safe thresholds
    And saving the health policy with a minimum sample of 0 is refused with status 400
    When I switch the health policy on with a minimum sample of 30 and a bounce limit of 4 percent
    Then the health policy is on with a minimum sample of 30 and a bounce limit of 4 percent

  Scenario: Q15 a sent message shows up in the health of its route and of the channel
    Given the q15 route "bdd-q15-a" exists
    And the health of the route "bdd-q15-a" is read as "before"
    When I queue an approved "followup" message to "bdd-q15-a1@example-shop-1.test" on the q15 route "bdd-q15-a" as "saved.q15a"
    And the beat send task has run
    Then the outbound message "saved.q15a" has status "sent"
    And the route "bdd-q15-a" has sent 1 more in the 24h and 7d windows than "before"
    And the channel health covers at least the sent count of "bdd-q15-a"

  Scenario: Q15 a paused route holds its mail while another route keeps sending, a resume needs a reason
    Given the q15 route "bdd-q15-b" exists
    And the q15 route "bdd-q15-c" exists
    When I pause the route "bdd-q15-b" with the reason "bdd check of the brake"
    And I queue an approved "followup" message to "bdd-q15-b1@example-shop-1.test" on the q15 route "bdd-q15-b" as "saved.q15b"
    And I queue an approved "followup" message to "bdd-q15-c1@example-shop-1.test" on the q15 route "bdd-q15-c" as "saved.q15c"
    And the beat send task has run
    Then the outbound message "saved.q15b" has status "approved"
    And the outbound message "saved.q15c" has status "sent"
    And the route "bdd-q15-b" is paused
    And pausing the route "bdd-q15-b" again is refused with status 409
    And resuming the route "bdd-q15-b" without a reason is refused with status 400
    When I resume the route "bdd-q15-b" with the reason "bdd brake released"
    And the beat send task has run
    Then the route "bdd-q15-b" is not paused
    And the outbound message "saved.q15b" has status "sent"
    And the pause log lists "pause" then "resume" for "bdd-q15-b" with the reasons
