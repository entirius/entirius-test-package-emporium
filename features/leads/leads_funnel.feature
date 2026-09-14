@leads @funnel @leads-oneshot
Feature: Leads funnel — a CSV row to a reply in the notification bar
  As a sales operator
  I want one imported company to go through audit, draft, review, send, reply and escalation on its own
  So that the four leads platform modules are proven to work together in Volkanos

  Reference scenario of the leads platform (mode A of guides/leads-end-to-end-testing in entirius-docs), one
  scenario per step so a failure names the step. Scenarios run in order and each finds its state again through
  the admin API. Company example-shop-1.test is reserved for this feature (package/leads--funnel.csv).
  One-shot: the import, audit, draft and reply are consumed — re-run after `make seed`. Mailbox checks never
  count the whole mailbox: send-due also delivers what earlier features left due, so they filter by recipient
  or subject, and step 8 compares with the count saved in the Background. The import goes through `test/import-now/` (the queued import
  needs a temp dir shared by service and worker). A company created by the import starts in `new` without a
  `stage_entered` signal, so step 2 runs the stage rules through `test/evaluate/`. Recordings of example-shop-1.test cover
  lighthouse and urlscan; it has no synthetic site, so the heuristic source fails and the audit ends
  `partially_completed`. No notification is raised for a new draft (the review queue is the signal). A reply raises two `high` notifications (communicator and leads), both escalate by
  email. T-07 is covered by step 3 (hooks and draft from the fake model; one contact, so no recipient pick); the tracker entries are not asserted here — the toolbox runs outside zeno.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the sandbox mailbox count is remembered
    And the channel clock is monday 10:00

  Scenario: Funnel 0 the four modules are registered and the communicator channel is in sandbox
    Then the munin registry lists the modules "leads, communicator, siteintel, notifications"
    When I GET the v2 admin endpoint "communicator/admin/{channel_idx}/channel/"
    Then the response status should be 200
    And the response field "mode" should equal "sandbox"

  Scenario: Funnel 1 a CSV row becomes a new company
    When I upload the package file "leads--funnel.csv" to the v2 admin endpoint "leads/admin/{channel_idx}/test/import-now/"
    Then the response status should be 200
    And I save the response field "id" as "batch_id"
    And the import batch "batch_id" has finished
    And the response field "created_count" should equal integer 1
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-1.test"
    Then the response field "count" should equal integer 1
    And I save the first result field "id" as "company_id"
    And the company "company_id" is in stage "new"
    And the company "company_id" has an activity "import" containing "import created"

  Scenario: Funnel 2 the stage rule requests an audit that finishes with processed reports
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-1.test"
    Then I save the first result field "id" as "company_id"
    When I run the leads test action "evaluate" with body
      """
      {"company_id": {company_id}, "trigger": "stage_entered", "stage_key": "new"}
      """
    Then the company "company_id" has a rule run "fired"
    And the company "company_id" has an activity "intel" containing "audit requested"
    When I GET the v2 admin endpoint "siteintel/admin/{channel_idx}/audits/?domain=example-shop-1.test"
    Then I save the first result field "id" as "audit_id"
    When the audit test run of "audit_id" has completed
    Then I wait up to 60 seconds until the v2 admin endpoint "siteintel/admin/{channel_idx}/audits/{audit_id}/" field "status" equals "partially_completed"
    And the report for source "lighthouse" should have processed field "strategies" set
    And the report for source "urlscan" should have status "completed"
    And the report for source "heuristic" should have status "failed"

  Scenario: Funnel 3 the analysis finds hooks, picks the recipient and leaves a draft to review
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-1.test"
    Then I save the first result field "id" as "company_id"
    And the company "company_id" has an activity "intel" containing "intel analysed"
    And the company "company_id" has 3 hooks and a platform
    And the company "company_id" has an activity "draft" containing "draft review_required"
    And the review queue holds a draft about the company "company_id"

  Scenario: Funnel 4 the reviewer accepts the draft
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-1.test"
    Then I save the first result field "id" as "company_id"
    Given the review draft about the company "company_id" is saved as "draft"
    When I accept the message "draft"
    Then the response status should be 200
    And the response field "status" should equal "approved"
    And the response field "scheduled_at" should not be null

  Scenario: Funnel 5 the beat sends the message into the sandbox with footer and both parts
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-1.test"
    Then I save the first result field "id" as "company_id"
    When the beat send task has run
    Then the sandbox mailbox holds 1 messages to "anna@example-shop-1.test"
    And the sandbox message to "anna@example-shop-1.test" has a subject starting with "[SANDBOX]"
    And the sandbox message to "anna@example-shop-1.test" is multipart/alternative with our Message-ID
    And the sandbox message to "anna@example-shop-1.test" has a text and an html part containing "placeholder for legitimate interest, PL"

  Scenario: Funnel 6 a reply to the sent message marks the thread replied
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-1.test"
    Then I save the first result field "id" as "company_id"
    Given the sent message about the company "company_id" is saved as "outreach"
    When the fixture mail "reply_plain.eml" arrives replying to "outreach"
    And the communicator inbox has been polled
    Then the thread of "outreach" has status "replied"
    And the last reply in the thread of "outreach" has kind "reply" matched by "header"

  Scenario: Funnel 7 leads moves the company to replied and the unread alert escalates by email
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=example-shop-1.test"
    Then I save the first result field "id" as "company_id"
    Given the sent message about the company "company_id" is saved as "outreach"
    Then the company "company_id" is in stage "replied"
    And the company "company_id" has an activity "reply" containing "reply received"
    And the thread of "outreach" has 2 "high" notifications
    When I run the notifications escalation 2 minutes from now
    Then the response status should be 200
    And the sandbox mailbox receives a message with the subject "Reply from Example Shop 1"

  Scenario: Funnel 8 a blocked contact gets no draft and no mail
    Given the leads contact "blocked@example-shop-9.test" of the company "example-shop-7.test" is saved as "blocked"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/companies/{blocked.company}/communicate/" with body
      """
      {"template_key": "lead.cold.b2b", "contact_id": {blocked}}
      """
    Then the response status should be 409
    And the company "blocked.company" has an activity "blocked" containing "blocked: do_not_contact"
    And the review queue holds no draft about the company "blocked.company"
    When the communicator beat sends due messages
    Then the sandbox mailbox count is unchanged
