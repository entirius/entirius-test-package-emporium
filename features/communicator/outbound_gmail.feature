@communicator @outbound-gmail
Feature: Outbound mail through the Gmail API
  As a sales operator
  I want to connect a Google Workspace mailbox and send and receive through it
  So that one connected account replaces SMTP send-as and an extra forwarded IMAP mailbox

  Outbound Gmail API chain (entirius-infra/outbound/work/gmail-api-chain.md). Needs the communicator branch with migration
  0018 and a Gmail API test double (tests/gmail_stub.py of the communicator) reachable from the API and from this package:
  GMAIL_STUB_URL (default http://localhost:8199) is the double as the test sees it. The API host must have
  COMMUNICATOR_GMAIL_CLIENT_ID / _CLIENT_SECRET / _REDIRECT_URI and the COMMUNICATOR_GMAIL_*_URL settings pointed at the
  double; nothing here talks to Google. Run with `make bdd TAGS=@outbound-gmail`. Every scenario makes its own account (a
  unique address) and routes and removes them afterwards.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the gmail test double is reset
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "sandbox" mode
    And the beat has drained every due message

  Scenario: Gmail connect an account over OAuth, with no token in any answer
    Given a gmail account "gm1" exists
    Then the gmail account "gm1" is "not_connected"
    When I connect the gmail account "gm1" at the test double
    Then the gmail account "gm1" is "connected"
    And the test double saw an offline consent request with PKCE for "gm1" asking only for the send permission
    And no gmail account answer contains a token
    And the connection test of the gmail account "gm1" passes

  Scenario: Gmail a mail leaves through the Gmail API with the unsubscribe header and the DW mailbox
    Given a gmail account "gm2" exists
    And I connect the gmail account "gm2" at the test double
    And the gmail route "bdd-gm2" sends through the account "gm2" with the DW mailbox "dw-gm2@entirius.example.test"
    When I queue an approved "followup" message to "bdd-gm2-a@example-shop-1.test" on the gmail route "bdd-gm2" as "saved.gm2"
    And the beat send task has run
    Then the outbound message "saved.gm2" has status "sent"
    And the test double holds 1 message sent by the account "gm2"
    And that message is from the account "gm2" with a one-click List-Unsubscribe header and the DW mailbox "dw-gm2@entirius.example.test" kept out of the sandbox

  Scenario: Gmail a revoked account holds its route, other routes keep sending, a new sign-in releases the mail
    Given a gmail account "gm3" exists
    And I connect the gmail account "gm3" at the test double
    And the gmail route "bdd-gm3" sends through the account "gm3" with the DW mailbox "dw-gm3@entirius.example.test"
    And a plain route "bdd-gm3-smtp" exists
    When the user revokes the access of the account "gm3" in Google
    And I queue an approved "followup" message to "bdd-gm3-a@example-shop-1.test" on the gmail route "bdd-gm3" as "saved.gm3a"
    And I queue an approved "followup" message to "bdd-gm3-b@example-shop-1.test" on the gmail route "bdd-gm3-smtp" as "saved.gm3b"
    And the beat send task has run
    Then the gmail account "gm3" shows the state "needs_reauth" and the error "invalid_grant"
    And the outbound message "saved.gm3a" has status "approved"
    And the outbound message "saved.gm3b" has status "sent"
    And the test double holds 0 messages sent by the account "gm3"
    When I connect the gmail account "gm3" at the test double
    And the beat send task has run
    Then the gmail account "gm3" is "connected"
    And the outbound message "saved.gm3a" has status "sent"
    And the test double holds 1 message sent by the account "gm3"

  Scenario: Gmail a reply read through the Gmail API lands in the thread of the sent mail
    Given a gmail account "gm4" exists that also reads replies
    And I connect the gmail account "gm4" at the test double
    And the gmail route "bdd-gm4" sends through the account "gm4" with the DW mailbox "dw-gm4@entirius.example.test"
    When I queue an approved "followup" message to "bdd-gm4-a@example-shop-1.test" on the gmail route "bdd-gm4" as "saved.gm4"
    And the beat send task has run
    Then the outbound message "saved.gm4" has status "sent"
    When the recipient replies to the mail sent through the account "gm4"
    And the communicator inbox has been polled
    Then the last reply in the thread of "saved.gm4" has kind "reply" matched by "header"
    When the communicator inbox has been polled
    Then the thread of "saved.gm4" has exactly 1 reply
