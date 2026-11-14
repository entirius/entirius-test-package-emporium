@communicator @leads @crm @crm-outbound
Feature: CRM mailboxes, the approval inbox, one-click unsubscribe and do-not-contact
  As a salesperson
  I want my mail to leave from my own mailbox within safe limits, every draft in one inbox, and a recipient able to
  leave with one click
  So that outreach stays personal, reviewable in bulk and compliant

  Data: the seed's two mailboxes (scripts/seed-crm.py): `manager` (the channel default, sales1@greenmail.test) and
  `editor` (sales2@greenmail.test), each with its own GreenMail login. The channel stays in sandbox mode, so every
  mail lands in the sandbox mailbox with its original recipient in `X-Original-To`. Every scenario imports its own
  company or writes to its own address; a changed cap, pause, policy or suppression is put back when the scenario
  ends. The one-click scenarios need `COMMUNICATOR_UNSUBSCRIBE_BASE_URL` (zeno sets it to the service URL).

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "dry_run" mode
    And the beat has drained every due message
    And the communicator channel is in "sandbox" mode
    And the sequence "followup" is the autostart sequence of the channel

  Scenario: Mail of a company leaves from its owner's mailbox
    Given a fresh company owned by the editor staff user is imported as "company"
    When the company "company" is contacted with the static mail "reply.thanks"
    Then the sandbox mail to the contact of "company" is from "sales2@greenmail.test"

  Scenario: Mail of a company without an owner leaves from the channel's default mailbox
    Given a fresh company is imported as "company"
    When the company "company" is contacted with the static mail "reply.thanks"
    Then the sandbox mail to the contact of "company" is from "sales1@greenmail.test"

  Scenario: A mailbox with a daily cap of one sends one mail and keeps the next one waiting
    Given the mailbox of the editor staff user has a daily cap of 1
    And a fresh company owned by the editor staff user is imported as "first"
    And a fresh company owned by the editor staff user is imported as "second"
    When the company "first" is approved for the static mail "reply.thanks"
    And the company "second" is approved for the static mail "reply.thanks"
    And the beat send task has run
    Then the mail of the company "first" has status "sent"
    And the mail of the company "second" has status "approved"

  Scenario: The approval inbox filters drafts by mailbox
    Given a fresh company owned by the editor staff user is imported as "mine"
    And a fresh company owned by the manager staff user is imported as "theirs"
    When the company "mine" gets a draft of the static mail "reply.thanks"
    And the company "theirs" gets a draft of the static mail "reply.thanks"
    Then the approval inbox of the editor's mailbox holds the draft of "mine" and not the draft of "theirs"

  Scenario: The approval row of a company's draft carries the company name
    Given a fresh company is imported as "company"
    When the company "company" gets a draft of the static mail "reply.thanks"
    Then the approval row of the draft of "company" carries the company name

  Scenario: A paused mailbox holds its mail while another mailbox keeps sending; resuming needs a reason
    Given a fresh company owned by the editor staff user is imported as "held"
    And a fresh company owned by the manager staff user is imported as "sent"
    When the company "held" is approved for the static mail "reply.thanks"
    And the company "sent" is approved for the static mail "reply.thanks"
    And the mailbox of the editor staff user is paused with the reason "bdd pause"
    And the beat send task has run
    Then the mail of the company "held" has status "approved"
    And the mail of the company "sent" has status "sent"
    And the health of the editor's mailbox reports the state "paused"

  Scenario: A sent mail counts in the health of its mailbox
    Given a fresh company owned by the manager staff user is imported as "company"
    When the company "company" is contacted with the static mail "reply.thanks"
    Then the health of the manager's mailbox reports at least 1 mail sent today

  Scenario: A bulk approve and a bulk reject change the drafts, name what failed and are logged
    Given a fresh company is imported as "approve"
    And a fresh company is imported as "reject"
    When the company "approve" gets a draft of the static mail "reply.thanks"
    And the company "reject" gets a draft of the static mail "reply.thanks"
    And the drafts of "approve" and a missing message are approved in bulk
    Then the bulk answer lists the draft of "approve" as done and the missing message as failed
    And the mail of the company "approve" has status "approved"
    When the draft of "reject" is rejected in bulk with the reason "bdd reject"
    Then the mail of the company "reject" has status "rejected"
    And the bulk approval log starts with a "reject" entry

  Scenario: A bulk request above the size limit is refused and changes nothing
    When 101 draft ids are approved in bulk
    Then the response status should be 400

  Scenario: A forged unsubscribe token is refused
    When the unsubscribe link "not-a-real-token" is posted as a one-click request
    Then the response status should be 400

  Scenario: A mail carries the one-click headers and posting its link suppresses the address
    When an approved "followup" message to a fresh address "unsub" has been sent
    Then the sandbox mail to the contact of "unsub" carries the one-click unsubscribe headers
    When the unsubscribe link of the sandbox mail to the contact of "unsub" is opened
    Then the response status should be 200
    And the suppression list does not contain the address of "unsub"
    When the unsubscribe link of the sandbox mail to the contact of "unsub" is posted as a one-click request
    Then the response status should be 200
    And the address of "unsub" is refused as "suppressed"

  Scenario: A mail for a template that needs the legal footer is not created without one
    When I POST to the v2 admin endpoint "communicator/admin/{channel_idx}/test/communicate/" with body
      """
      {"template_key": "followup", "recipient": {"email": "bdd-crm-footer@example-shop-1.test", "language": "pl"},
       "context": {"company_name": "Example Shop 1"}, "subject_ref": "bdd:crm:footer", "requires_review": false}
      """
    Then the response status should be 400

  Scenario: The auto-pause policy is off by default, validated and saved
    Given the auto-pause policy is put back when the scenario ends
    When I GET the v2 admin endpoint "communicator/admin/{channel_idx}/health/policy/"
    Then the response status should be 200
    And the response field "enabled" should be false
    When I PUT to the v2 admin endpoint "communicator/admin/{channel_idx}/health/policy/" with body
      """
      {"enabled": true, "window_hours": 168, "min_sample": 50, "max_bounce_pct": -1, "max_optout_pct": 3, "max_complaint_pct": 0.1}
      """
    Then the response status should be 400
    When I PUT to the v2 admin endpoint "communicator/admin/{channel_idx}/health/policy/" with body
      """
      {"enabled": true, "window_hours": 72, "min_sample": 50, "max_bounce_pct": 2, "max_optout_pct": 3, "max_complaint_pct": 0.1}
      """
    Then the response status should be 200
    And the response field "window_hours" should equal integer 72

  Scenario: A contact with a legal basis is mailable and the answer says why
    Given a fresh company is imported as "company"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/{company}/contacts/{company.contact}/mailable/"
    Then the response status should be 200
    And the response field "eligible" should be true
    And the nested response field "legal_basis.value" should equal "legitimate_interest"

  Scenario: An address on the channel's do-not-contact list stops the contact
    Given a fresh company is imported as "company"
    And the address of "company" is on the do-not-contact list of the channel
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/{company}/contacts/{company.contact}/mailable/"
    Then the response field "eligible" should be false
    And the response field "reasons" should contain "suppressed"
    And the do-not-contact entry of "company" holds on the channel only

  Scenario: A do-not-contact entry added for all channels is listed as global and refuses mail to the address
    Given a fresh company is imported as "company"
    And the address of "company" is on the do-not-contact list of all channels
    Then the do-not-contact list shows the address of "company" for all channels
    And the address of "company" is refused as "suppressed"
    When a "followup" message to the address of "company" is requested
    Then the requested message to "company" has status "suppressed"

  # Live sending exists only in production (`channel_service.live_allowed`), so the beat never judges a zeno channel.
  # The scenario runs the module's own health check once in the service container on the channel as it would be in
  # live mode (the mode is set in memory, never saved): real sent mail and a real hard bounce from the sandbox.
  Scenario: A live mailbox over the bounce threshold is paused by itself and only a person resumes it
    Given the auto-pause policy is enabled with a bounce limit of 0 percent after 1 mail
    And the mailbox of the manager staff user is resumed when the scenario ends
    And an approved "followup" message to a fresh address "pause" has been sent
    When a hard bounce of the mail to the address of "pause" arrives
    And the inbox is polled until the thread of "pause" has a reply
    And the health check of the channel in live mode has run
    Then the health of the manager's mailbox reports the state "paused"
    And the pause log starts with an automatic pause for "bounce"

  Scenario: The login test of a seeded mailbox logs in the way a send does
    Then the login test of the mailbox of the manager staff user answers "ok" for SMTP and IMAP
    And the login test of the mailbox of the editor staff user answers "ok" for SMTP and IMAP
