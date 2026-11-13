@leads @communicator @todo @crm @crm-core
Feature: CRM core — owners, custom fields, tasks, the today list and mail written by hand
  As a salesperson
  I want my companies, my own fields, my tasks for the day and a mail I write myself from the company card
  So that the whole selling day happens in one place

  Data: the seed's staff users `manager` and `editor` with their mailboxes, the company attribute `segment_size`
  (a select shown in the list) and the scoring profile (scripts/seed-crm.py). Every scenario imports its own company
  with a unique domain and address; rules and attribute definitions a scenario creates are deleted when it ends, so
  `make bdd TAGS=@crm` can be re-run on one database. The due reminder is the beat task `django_todo.remind_due`, run
  once in the service container (`SERVICE_CONTAINER`, zeno `make bdd` passes it).

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "sandbox" mode
    And the sequence "followup" is the autostart sequence of the channel

  Scenario: A salesperson filters the company list to their own companies
    Given a fresh company owned by the editor staff user is imported as "company"
    Then the company "company" is in the editor staff user's list filtered by the owner "me"
    And the company "company" is not in the manager staff user's list filtered by the owner "me"

  Scenario: An alert about a company goes to its owner only
    Given a fresh company owned by the editor staff user is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Call me tomorrow" with the class "interested"
    Then the editor staff user has the reply alert about the company "company"
    And the manager staff user has no reply alert about the company "company"

  Scenario: A classified reply rings the owner's bell once, in words
    Given a fresh company owned by the editor staff user is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Not this quarter" with the class "not_now"
    Then the editor staff user has one reply alert about the company "company" titled with "Not now"

  Scenario: A field is defined, read back and deleted while no company holds a value
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/attributes/" with body
      """
      {"entity": "company", "key": "bdd_crm_field", "label": "BDD field", "kind": "text"}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.attribute"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/fields/"
    Then the item with "name" equal to "attr.bdd_crm_field" should exist
    When I DELETE the v2 admin endpoint "leads/admin/{channel_idx}/attributes/{saved.attribute}/"
    Then the response status should be 204

  Scenario: A field is imported from its CSV column and filters the company list
    Given a fresh company is imported as "company" with the columns
      | column            | value  |
      | attr.segment_size | medium |
    Then the company "company" has the field "segment_size" equal to "medium"
    And the company "company" is in the list filtered by the field "segment_size" equal to "medium"
    And the company "company" is not in the list filtered by the field "segment_size" equal to "large"

  Scenario: A rule condition on a field decides whether the rule fires
    Given an active scoring rule on the stage "new" for companies whose "attr.segment_size" is "large"
    And a fresh company is imported as "large" with the columns
      | column            | value |
      | attr.segment_size | large |
    And a fresh company is imported as "small" with the columns
      | column            | value |
      | attr.segment_size | small |
    When the rules of the stage "new" are evaluated for the companies "large" and "small"
    Then the scoring rule fired for "large" and was skipped for "small"

  Scenario: A task is created about a company, shows on the owner's today list and closes with an outcome
    Given a fresh company owned by the editor staff user is imported as "company"
    When a phone task "Call the owner" due now is created about the company "company" for the editor staff user
    Then the task of the company "company" is on the today list of the editor staff user
    When the task of the company "company" is done with the outcome "talked, sending an offer"
    Then the company "company" has an activity "task" containing "done: Call the owner"

  Scenario: A due task rings the owner's bell once
    Given a fresh company owned by the editor staff user is imported as "company"
    When a phone task "Call back" due now is created about the company "company" for the editor staff user
    And the due reminder has run
    Then the editor staff user has a notification about the task of the company "company"

  Scenario: A mail written by hand leaves from the owner's mailbox and stops the sequence
    Given a fresh company owned by the editor staff user is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When a mail "BDD hand-written" is written by hand to the contact of "company"
    Then the response status should be 201
    And the sequence of the company "company" is stopped with reason "manual"
    When the beat send task has run
    Then the sandbox mail "BDD hand-written" to the contact of "company" is from "sales2@greenmail.test"

  Scenario: A mail written by hand to an opted-out contact is refused
    Given a fresh company is imported as "company"
    And the address of "company" is on the do-not-contact list of the channel
    When a mail "BDD hand-written" is written by hand to the contact of "company"
    Then the response status should be 409
    And the error response should have error code "NOT_ELIGIBLE"
