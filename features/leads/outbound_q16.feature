@leads @communicator @outbound-q16
Feature: Outbound — what to do today, the "not now" loop and the daily digest
  As a salesperson
  I want one list of what needs me today, a "not now" to come back by itself and a morning summary
  So that nothing waits unseen and nobody is written to who should not be

  Roadmap Q16 (queue, digest) and Q20 ("not now" loop), entirius-infra/outbound/work/q16-q20-leads.md. Needs the leads
  build with migration 0014, the communicator with T4 and the AI toolbox answering reply-intent requests (@needs-toolbox
  scenarios, like outbound_t4.feature). The resume run is driven through `test/resume-now/` with a clock moved forward,
  because the daily task is off by default and a 30-day wait cannot be waited for. Every scenario makes its own company;
  every setting it changes is put back when it ends. Run: `make bdd TAGS=@outbound-q16`.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "sandbox" mode
    And the sequence "followup" is the autostart sequence of the channel
    And a fresh company is imported as "company_id"
    When the company "company_id" is contacted with the static mail "reply.thanks"

  @needs-toolbox @q20
  Scenario: Q20 a "not now" reply plans the return and the resume drafts again through the gate
    When a reply with the text "Nie teraz, wróćmy do tematu w przyszłym kwartale." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "reply" and intent "not_now"
    And the first contact of the company "company_id" has a planned return as "not_now" in about 30 days
    And the company "company_id" has an activity "resume" containing "resume planned"
    When the "not now" resume of the company "company_id" runs 5 days ahead
    Then the resume run resumed 0 contacts and cancelled 0
    When the "not now" resume of the company "company_id" runs 31 days ahead
    Then the resume run resumed 1 contacts and cancelled 0
    And the first contact of the company "company_id" has no planned return
    And the company "company_id" has an activity "resume" containing "resumed: draft requested"
    And the queue of the channel has a "drafts" row linking to "/leads/approvals"

  @needs-toolbox @q20
  Scenario: Q20 the window without a date is set per channel
    Given the "not now" window of the channel is 45 days
    When a reply with the text "Nie teraz, wróćmy do tematu w przyszłym kwartale." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the first contact of the company "company_id" has a planned return as "not_now" in about 45 days

  @needs-toolbox @q20
  Scenario: Q20 nobody is resumed after an unsubscribe
    When a reply with the text "Nie teraz, wróćmy do tematu w przyszłym kwartale." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the first contact of the company "company_id" has a planned return as "not_now" in about 30 days
    When the address of the first contact of the company "company_id" is put on the do-not-contact list
    And the "not now" resume of the company "company_id" runs 31 days ahead
    Then the resume run resumed 0 contacts and cancelled 1
    And the first contact of the company "company_id" has no planned return
    And the company "company_id" has an activity "resume" containing "resume cancelled: blocked: opted_out"

  @needs-toolbox @q16
  Scenario: Q16 a reply that needs a person and the contact to decide are in the queue, sorted by value
    When a reply with the text "To nie ta osoba. Proszę skontaktować się z działem e-commerce." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "reply" and intent "wrong_person"
    And the queue of the channel has a "reply" row for the company "company_id" with reason "wrong_person"
    And the queue of the channel has a "decision" row for the company "company_id" with reason "wrong_person"
    And the queue of the channel is sorted by value

  @q16
  Scenario: Q16 the daily digest says what the automation did and goes to notifications
    When the daily digest is sent
    Then the digest reached notifications and counts at least 1 sent mail
