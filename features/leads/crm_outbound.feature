@leads @communicator @crm @crm-outbound
Feature: CRM outbound loop — import, first mail, follow-ups, replies with a class, scoring and the funnel
  As a salesperson
  I want the mail loop to run without a person starting each step, and every reply to come with a next step
  So that only reading a draft and answering a reply needs me

  Data: the seed's CRM configuration (scripts/seed-crm.py): the event map first mail sent -> contacted, a reply ->
  replied, an out-of-office reply keeps the stage; the scoring profile (a large company +20, a retailer +10, a
  competitor is disqualified). The follow-up sequence is the autostart sequence for the length of a scenario only.
  Every scenario imports its own company with a unique domain and address, so none consumes the seed and
  `make bdd TAGS=@crm` can be re-run on one database. Replies get their class through the development endpoint `test/ingest-reply/` — no toolbox is needed.
  The static `reply.thanks` template stands in for the AI drafts.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "sandbox" mode
    And the sequence "followup" is the autostart sequence of the channel

  Scenario: An import without rules creates the company in its first stage and runs nothing
    When a fresh company is imported as "company"
    Then the company "company" is in stage "new"
    And the company "company" has no rule run

  Scenario: An import with the rules on runs the rules of the first stage
    When a fresh company is imported as "company" with the rules on
    Then the company "company" is in stage "new"
    And the company "company" has a rule run "fired"

  Scenario: The import report names a column it did not read
    When a fresh company is imported as "company" with the columns
      | column  | value |
      | bdd_fax | 123   |
    Then the import report names the ignored column "bdd_fax"

  Scenario: The first sent mail moves the company to contacted
    Given a fresh company is imported as "company"
    When the company "company" is contacted with the static mail "reply.thanks"
    Then the company "company" is in stage "contacted"
    And the company "company" has an activity "stage" containing "new -> contacted"

  Scenario: The autostart sequence starts after the first delivery
    Given a fresh company is imported as "company"
    When the company "company" is contacted with the static mail "reply.thanks"
    Then the thread of the company "company" runs the sequence "followup" with a follow-up due

  Scenario: A natural refusal is a suspected opt-out
    Given a sandbox message to "bdd-crm-optout@example-shop-8.test" has been sent as "optout"
    When the fixture mail "reply_optout_natural_pl.eml" arrives replying to "optout"
    And the communicator inbox has been polled
    Then the last reply in the thread of "optout" has kind "suspected_optout" matched by "header"

  Scenario: An interested reply stops the sequence, moves the company to replied and asks for an answer
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Sounds good, call me" with the class "interested"
    Then the sequence of the company "company" is stopped with reason "replied"
    And the company "company" is in stage "replied"
    And the company "company" has an open task "Interested"

  Scenario: A "not now" reply pauses the sequence and leaves a task with a due day
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Not this quarter" with the class "not_now"
    Then the sequence of the company "company" is stopped with reason "paused"
    And the company "company" has an open task "Come back"
    And the task of the company "company" is due in 30 days

  Scenario: An out-of-office reply keeps the stage and pauses the sequence until the return date
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Away until next month" with the class "out_of_office" back on 2026-10-05
    Then the company "company" is in stage "contacted"
    And the sequence of the company "company" is stopped with reason "paused"
    And the company "company" has no open task

  Scenario: A wrong-person reply flags the contact and asks a person to read it
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "I left the company" with the class "wrong_person"
    Then the contact of "company" is marked as the wrong person
    And the last reply about the company "company" needs review
    And the company "company" has an open task "Read the reply"

  Scenario: An unsubscribe in unknown wording waits for a person before anybody is suppressed
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Please take me off" with the class "unsubscribe"
    Then the last reply about the company "company" has the kind "suspected_optout"
    And the suppression list does not contain the address of "company"

  Scenario: A not interested reply stops the sequence and leaves no task
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "No thanks" with the class "not_interested"
    Then the sequence of the company "company" is stopped with reason "replied"
    And the company "company" has no open task

  Scenario: An unclear reply waits for a person
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Hm?" with the class "unclear"
    Then the last reply about the company "company" needs review
    And the company "company" has an open task "Read the reply"

  Scenario: A reply without a class is handled as before and asks a person to read it
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Thanks for writing" without a class
    Then the company "company" is in stage "replied"
    And the sequence of the company "company" is stopped with reason "replied"
    And the company "company" has an open task "Read the reply"

  Scenario: The plan of a reply class can be read, changed and put back
    When I PUT to the v2 admin endpoint "communicator/admin/{channel_idx}/reply-classes/plans/not_interested/" with body
      """
      {"sequence": "stop", "notify": "high", "needs_review": true}
      """
    Then the response status should be 200
    And the response field "needs_review" should be true
    When I GET the v2 admin endpoint "communicator/admin/{channel_idx}/reply-classes/plans/"
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "communicator/admin/{channel_idx}/reply-classes/plans/not_interested/"
    Then the response status should be 200
    And the response field "is_default" should be true
    And the response field "needs_review" should be false

  Scenario: The event map moves a company on a reply class and can be put back
    When I PUT to the v2 admin endpoint "leads/admin/{channel_idx}/stage-events/reply:not_interested/" with body
      """
      {"target_stage_key": "lost", "forward_only": true}
      """
    Then the response status should be 200
    And the response field "target_stage_key" should equal "lost"
    When I DELETE the v2 admin endpoint "leads/admin/{channel_idx}/stage-events/reply:not_interested/"
    Then the response status should be 204
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/stage-events/"
    Then the item with "event" equal to "first_sent" should exist

  Scenario: A large retailer scores 30 points and lands in S1
    Given a fresh company is imported as "company" with the columns
      | column            | value        |
      | attr.segment_size | large        |
    And the company "company" industry is "retail"
    When the company "company" is scored
    Then the score is segment "S1" with 30 points

  Scenario: Scoring a company while the channel has no active profile is refused
    Given the scoring profile of the channel is switched off
    And a fresh company is imported as "company"
    When the company "company" is scored
    Then the response status should be 409
    And the error response should have error code "NO_SCORING_PROFILE"

  Scenario: A disqualifier forces S4 whatever the points
    Given a fresh company is imported as "company" with the columns
      | column            | value |
      | attr.segment_size | large |
    And the company "company" industry is "competitor retail"
    When the company "company" is scored
    Then the score is segment "S4" and disqualified

  Scenario: The funnel report counts a stage transition for one origin
    Given a fresh company is imported as "company" with the columns
      | column | value              |
      | origin | bdd-crm-{unique}   |
    When the company "company" moves through the stages "contacted"
    Then the funnel report of the origin of "company" shows 1 company and a transition "new" to "contacted"

  # The report answers 200 with an empty period today; the module does not refuse a reversed window yet.
  @blocked-by-module
  Scenario: A funnel window that ends before it starts is refused
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/reports/funnel/?date_from=2026-09-30&date_to=2026-09-01"
    Then the response status should be 400

  Scenario: An origin nobody uses gives an empty funnel
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/reports/funnel/?origin=bdd-crm-no-such-origin"
    Then the response status should be 200
    And the response field "transitions" should be an empty list
    And the response field "origins" should be an empty list

  Scenario: Moving a company to an unknown stage is a 404
    Given a fresh company is imported as "company"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/companies/{company}/transition/" with body
      """
      {"stage_key": "bdd-no-such-stage"}
      """
    Then the response status should be 404

  Scenario: The company list filters by origin
    Given a fresh company is imported as "company" with the columns
      | column | value              |
      | origin | bdd-crm-{unique}   |
    Then the companies filtered by the origin of "company" are exactly "company"
