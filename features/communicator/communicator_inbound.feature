@communicator
Feature: Communicator — inbound replies, autoresponders, opt-outs and bounces
  As the sales team
  I want mail that answers our outreach attached to the right thread and acted on
  So that replies stop the sequence, opt-outs wait for a human and bounced addresses are never mailed again

  Data: fixtures/django_communicator.cfg.yaml (channel in sandbox mode, MailboxConfig polling the GreenMail
  sandbox INBOX over IMAP) and fixtures/mail/*.eml. Each scenario sends one sandbox message on a fresh
  thread, injects a fixture mail whose threading headers point at our Message-ID (a fresh inbound Message-ID
  per run), and runs the poll through test/poll-now/. It sends on tuesday with the cap raised by what the
  counter already holds (restored afterwards), so re-runs never starve the monday send scenarios. Our own sandbox copy in the INBOX is ignored by the poll.

  Background:
    Given I am authenticated as an admin user
    And the channel is the primary channel
    And the channel clock is tuesday 10:00
    And the communicator channel is in "sandbox" mode
    And the beat has drained every due message
    And the daily cap leaves room for 5 more messages today
    And the sandbox mailbox is empty

  Scenario: C-20 a reply with In-Reply-To marks the thread replied and notifies once
    Given a sandbox message to "owner@example-shop-1.test" has been sent as "c20"
    When the fixture mail "reply_plain.eml" arrives replying to "c20"
    And the communicator inbox has been polled
    Then the thread of "c20" has status "replied"
    And the last reply in the thread of "c20" has kind "reply" matched by "header"
    And the thread of "c20" has 1 "high" notifications

  Scenario: C-21 a reply without thread headers matches the newest open thread of the sender
    Given a sandbox message to "owner@example-shop-2.test" has been sent as "c21"
    When the fixture mail "reply_no_headers.eml" arrives replying to "c21"
    And the communicator inbox has been polled
    Then the thread of "c21" has status "replied"
    And the last reply in the thread of "c21" has kind "reply" matched by "sender"

  Scenario: C-22 an autoresponder changes nothing and notifies nobody
    Given a sandbox message to "office@example-shop-3.test" has been sent as "c22"
    When the fixture mail "autoresponder.eml" arrives replying to "c22"
    And the communicator inbox has been polled
    Then the last reply in the thread of "c22" has kind "auto" matched by "header"
    And the thread of "c22" has status "open"
    And the thread of "c22" has 0 "high" notifications
    And the thread of "c22" has 0 "medium" notifications

  Scenario: C-23 an opt-out phrase is a suspicion until a human confirms it
    Given a sandbox message to "owner@example-shop-4.test" has been sent as "c23"
    When the fixture mail "optout_pl.eml" arrives replying to "c23"
    And the communicator inbox has been polled
    Then the last reply in the thread of "c23" has kind "suspected_optout" matched by "header"
    And the thread of "c23" has 1 "medium" notifications
    When I confirm the opt-out of the last reply in the thread of "c23"
    Then the suppression list contains "owner@example-shop-4.test"

  Scenario: C-24 a hard bounce fails the message and suppresses the address
    Given a sandbox message to "owner@example-shop-6.test" has been sent as "c24"
    When the fixture mail "dsn_hard.eml" arrives replying to "c24"
    And the communicator inbox has been polled
    Then the last reply in the thread of "c24" has kind "bounce_hard" matched by "dsn"
    And the outbound message "c24" failed with code "bounce"
    And the suppression list contains "owner@example-shop-6.test"
    And the thread of "c24" has 1 "low" notifications
