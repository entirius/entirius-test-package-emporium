@leads @communicator @crm @crm-potential
Feature: CRM potential — a green, orange or red dot on every company we wrote to
  As a salesperson
  I want to see at a glance on the company list where the conversation goes on, waits or has to wait
  So that I spend the day where it is worth it

  Data: the seed's CRM configuration (scripts/seed-crm.py) and its deal pipeline. Every scenario imports its own
  company, so `make bdd TAGS=@crm-potential` re-runs on one database; the thresholds a scenario changes are put back
  when it ends. Replies get their class through `test/ingest-reply/` (no toolbox). The rules for later days (120 days
  of silence, the come-back days) are asked of the service in its container (`SERVICE_CONTAINER`, read only: nothing
  is stored for a day that has not come).

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "sandbox" mode

  Scenario: A company we never wrote to has no dot
    When a fresh company is imported as "company"
    Then the company "company" has no potential dot
    And the company "company" is in the list filtered by the potential "none"

  Scenario: A sent mail makes the company orange until a reply
    Given a fresh company is imported as "company"
    When the company "company" is contacted with the static mail "reply.thanks"
    Then the company "company" has the potential "orange" because "awaiting_reply"
    And the company "company" is in the list filtered by the potential "orange"
    And the company "company" has an activity "potential" containing "potential: orange"

  Scenario Outline: The last reply gives its colour
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "<text>" with the class "<intent>"
    Then the company "company" has the potential "<colour>" because "reply:<intent>"

    Examples:
      | intent         | text                    | colour |
      | interested     | Let us talk next week   | green  |
      | not_now        | Not this quarter        | orange |
      | out_of_office  | Away until Monday       | orange |
      | not_interested | We are not interested   | red    |

  Scenario: Not interested is red with a come-back day 90 days later
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "No, thank you" with the class "not_interested"
    Then the company "company" comes back in 90 days
    And in 91 days the service gives the company "company" the potential "orange" because "came_back"

  Scenario: Not now with a return date carries that date
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Write in spring" with the class "not_now" back on 2027-03-15
    Then the company "company" has the potential "orange" because "reply:not_now"
    And the company "company" comes back on "2027-03-15"

  Scenario: 120 days of silence after the last mail turn the company red, 90 days later it comes back
    Given a fresh company is imported as "company"
    When the company "company" is contacted with the static mail "reply.thanks"
    Then in 119 days the service gives the company "company" the potential "orange" because "awaiting_reply"
    And in 120 days the service gives the company "company" the potential "red" because "silence"
    And in 210 days the service gives the company "company" the potential "orange" because "came_back"

  Scenario: A skipped draft is orange and comes back to the queue after 30 days
    Given a fresh company is imported as "company"
    When the company "company" gets a draft of the static mail "reply.thanks"
    And the draft of the company "company" is skipped
    Then the company "company" has the potential "orange" because "draft_skipped"
    And the company "company" comes back in 30 days
    And the company "company" has an activity "skipped" containing "draft skipped"

  Scenario: A wrong person with nobody else to mail: we look for another person
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "I am not the right person" with the class "wrong_person"
    Then the company "company" has the potential "orange" because "looking_for_person"

  Scenario: An open deal makes the company green, every deal lost makes it red
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When a deal "BDD potential" worth "100.00" is opened on the company "company"
    Then the company "company" has the potential "green" because "deal_open"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/transition/" with body
      """
      {"kind": "lost", "lost_reason": "BDD price"}
      """
    Then the response status should be 200
    And the company "company" has the potential "red" because "deals_lost"

  Scenario: A colour set by hand needs a reason, carries a star and holds until a new reply
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the potential of the company "company" is set to "green" without a reason
    Then the response status should be 400
    When the potential of the company "company" is set to "green" with the reason "BDD met at a fair"
    Then the response status should be 200
    And the company "company" has the potential "green" set by hand with the reason "BDD met at a fair"
    And the company "company" has an activity "potential" containing "BDD met at a fair"
    When the contact of "company" replies "Not this quarter" with the class "not_now"
    Then the company "company" has the potential "orange" because "reply:not_now"

  Scenario: Back to automatic ends the colour set by hand
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    And the potential of the company "company" is set to "red" with the reason "BDD closed for the season"
    When the potential of the company "company" goes back to automatic
    Then the response status should be 200
    And the company "company" has the potential "orange" because "awaiting_reply"

  Scenario: Do not contact is red for good and takes no other colour by hand
    Given a fresh company is imported as "company"
    When I PATCH the v2 admin endpoint "leads/admin/{channel_idx}/companies/{company}/" with body
      """
      {"do_not_contact": true}
      """
    Then the company "company" has the potential "red" because "do_not_contact"
    And the company "company" has no come-back day
    When the potential of the company "company" is set to "green" with the reason "BDD please"
    Then the response status should be 409

  Scenario: The thresholds are settings of the channel
    Given the potential thresholds are put back when the scenario ends
    When I PATCH the v2 admin endpoint "leads/admin/{channel_idx}/channel/" with body
      """
      {"potential": {"silence_days": 60, "reply_colours": {"not_now": "red"}}}
      """
    Then the response status should be 200
    And the nested response field "potential.silence_days" should equal "60"
    And the nested response field "potential.skip_return_days" should equal "30"
    And the nested response field "potential.reply_colours.not_now" should equal "red"
    When I PATCH the v2 admin endpoint "leads/admin/{channel_idx}/channel/" with body
      """
      {"potential": {"silence_days": 0}}
      """
    Then the response status should be 400

  Scenario: A changed threshold recomputes the colours
    Given the potential thresholds are put back when the scenario ends
    And a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Not this quarter" with the class "not_now"
    And I PATCH the v2 admin endpoint "leads/admin/{channel_idx}/channel/" with body
      """
      {"potential": {"reply_colours": {"not_now": "red"}}}
      """
    Then the response status should be 200
    And the company "company" gets the potential "red" because "reply:not_now"
