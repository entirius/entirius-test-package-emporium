@leads @communicator @outbound-t4
Feature: Outbound replies are classified and the next step follows from the class
  As a sales operator
  I want a reply to be sorted (interested, not now, not interested, out of office, wrong person, unsubscribe, unclear)
  So that the sequence, the stage and the alerts follow without anyone reading every mail first

  Roadmap T4 (entirius-infra/outbound/roadmap.md), slices S10 (classes), S11 (next steps per class) and S12 (golden
  set, in the module tests). Classification needs the AI toolbox answering reply-intent requests, so those scenarios
  carry @needs-toolbox: against the zeno stack's own fake toolbox they would see a draft-shaped answer and fall back to
  "not classified", so run them with `outbound/checks/toolbox_stub.py` (deterministic keyword rules, Polish and
  English) and `COMMUNICATOR_REPLY_INTENT_MODEL` set. The scenarios without @needs-toolbox (mapping API, toolbox
  outage fallback) run anywhere. Every scenario makes its own company, so none consumes the seed; every setting it
  changes is put back when it ends. Run: `make bdd TAGS=@outbound-t4`.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "sandbox" mode
    And the sequence "followup" is the autostart sequence of the channel
    And a fresh company is imported as "company_id"
    When the company "company_id" is contacted with the static mail "reply.thanks"

  @needs-toolbox @t4-s10
  Scenario: S10 an interested reply is classified, stops the sequence and moves the company to replied
    When a reply with the text "Dzień dobry, chętnie porozmawiamy. Proszę o cennik." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "reply" and intent "interested"
    And the sequence about the company "company_id" is stopped with reason "replied"
    And the company "company_id" is in stage "replied"
    And the company "company_id" has an activity "reply" containing "interested"

  @needs-toolbox @t4-s11
  Scenario: S11 not now pauses the sequence, keeps a reminder and the reminder comes due
    When a reply with the text "Nie teraz, wróćmy do tematu w przyszłym kwartale." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "reply" and intent "not_now"
    And the sequence about the company "company_id" is stopped with reason "paused"
    And the last reply about the company "company_id" has "remind_at" set
    And the company "company_id" is in stage "replied"
    When the channel clock moves 31 days forward
    And the reply follow-ups have run
    Then the company "company_id" got a "medium" notification titled "Reminder"
    And the company "company_id" has an activity "note" containing "follow-up reminder"

  @needs-toolbox @t4-s11
  Scenario: S11 out of office pauses until the return date, leaves the stage and then resumes the sequence
    When a reply with the text "Jestem poza biurem do {in10}. Odpowiem po powrocie." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "reply" and intent "out_of_office"
    And the sequence about the company "company_id" is stopped with reason "paused"
    And the last reply about the company "company_id" has "resume_at" set
    And the company "company_id" is in stage "contacted"
    When the channel clock moves 12 days forward
    And the reply follow-ups have run
    Then the sequence about the company "company_id" is running

  @needs-toolbox @t4-s11
  Scenario: S11 not interested goes to the lost stage when the channel is set up that way
    Given the reply route of "not_interested" moves the company to the stage "lost"
    When a reply with the text "Dziękuję, nie jesteśmy zainteresowani." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "reply" and intent "not_interested"
    And the sequence about the company "company_id" is stopped with reason "replied"
    And the company "company_id" is in stage "lost"

  @needs-toolbox @t4-s11
  Scenario: S11 a wrong-person reply flags the contact, flags the reply and keeps the others reachable
    When a reply with the text "To nie ta osoba. Proszę skontaktować się z działem e-commerce." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has intent "wrong_person"
    And the last reply about the company "company_id" has "needs_review" set
    And the contact of the company "company_id" is flagged as the wrong person

  @needs-toolbox @t4-s10
  Scenario: S10 an unsubscribe in wording the phrase list does not know is a suspected opt-out until a person confirms
    When a reply with the text "Please stop emailing me." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "suspected_optout" and intent "unsubscribe"
    And the sequence about the company "company_id" is stopped with reason "paused"
    And the suppression list does not contain the address of the company "company_id"
    When I confirm the opt-out of the last reply about the company "company_id"
    Then the suppression list contains the address of the company "company_id"

  @needs-toolbox @t4-s11
  Scenario: S11 an unsubscribe is confirmed without a person only when the channel asks for it
    Given the reply action of "unsubscribe" asks for automatic suppression
    When a reply with the text "Please stop emailing me." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "suspected_optout" and intent "unsubscribe"
    And the suppression list contains the address of the company "company_id"
    And the sequence about the company "company_id" is stopped with reason "optout"

  @needs-toolbox @t4-s10
  Scenario: S10 an unclear reply waits for a person
    When a reply with the text "ok" arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "reply" and intent "unclear"
    And the last reply about the company "company_id" has "needs_review" set
    And the replies flagged for review include the last reply about the company "company_id"
    And the company "company_id" is in stage "replied"

  @toolbox-down @t4-s10
  Scenario: S10 with the toolbox down a reply is stored unclassified and handled as before
    Given the AI toolbox outage switch is on
    When a reply with the text "Chętnie, proszę o cennik." arrives for the company "company_id"
    And the communicator inbox has been polled
    Then the last reply about the company "company_id" has kind "reply" and no intent
    And the sequence about the company "company_id" is stopped with reason "replied"
    And the company "company_id" is in stage "replied"

  @t4-s11
  Scenario: S11 the next-step mapping can be read, changed and put back
    When I set the reply action of "not_now" to sequence "stop" and notify "low"
    Then the reply action of "not_now" is sequence "stop" and notify "low" and is not the default
    When I reset the reply action of "not_now"
    Then the reply action of "not_now" is sequence "pause" and notify "medium" and is the default
