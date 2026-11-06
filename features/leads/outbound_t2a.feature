@leads @outbound
Feature: Outbound loop gaps closed — import fires rules, first send moves the stage, follow-ups start by themselves
  As a sales operator
  I want the e-mail loop to run without a person starting each step
  So that only the review of a draft needs a human

  Roadmap T2a (entirius-infra/outbound/roadmap.md): F1 import fires the first-stage rules, F2 a sequence starts after
  the first delivery, F3 the first send moves the company to `contacted`, F4 a natural Polish refusal is a suspected
  opt-out. Every scenario makes its own company or address (unique per run), so none consumes the seed and all can
  be re-run: `make bdd TAGS=@outbound`. The sandbox channel and the Monday 10:00 clock are set per scenario. The static
  `reply.thanks` template stands in for the AI drafts, so no toolbox is needed.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the communicator channel is in "sandbox" mode

  @t2a-f1
  Scenario: F1 a company created by the import enters its first stage and the rules run
    When a fresh company is imported as "company_id"
    Then the company "company_id" is in stage "new"
    And the company "company_id" has an activity "intel" containing "audit requested"
    And the company "company_id" has a rule run "fired"

  @t2a-f3
  Scenario: F3 the first sent mail moves the company to contacted
    Given a fresh company is imported as "company_id"
    When the company "company_id" is contacted with the static mail "reply.thanks"
    Then the company "company_id" has an activity "sent" containing "message sent"
    And the company "company_id" is in stage "contacted"
    And the company "company_id" has an activity "stage" containing "new -> contacted"

  @t2a-f2
  Scenario: F2 the autostart sequence starts after the first delivery
    Given the sequence "followup" is the autostart sequence of the channel
    And a fresh company is imported as "company_id"
    When the company "company_id" is contacted with the static mail "reply.thanks"
    Then the first thread about the company "company_id" runs the sequence "followup" with a follow-up due

  @t2a-f4
  Scenario: F4 a natural Polish refusal is a suspected opt-out
    Given a sandbox message to "owner@example-shop-8.test" has been sent as "f4"
    When the fixture mail "reply_optout_natural_pl.eml" arrives replying to "f4"
    And the communicator inbox has been polled
    Then the last reply in the thread of "f4" has kind "suspected_optout" matched by "header"
