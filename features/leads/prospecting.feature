@leads @communicator @prospecting
Feature: U3 — another person to contact when the only one is the wrong person or opted out
  As a salesperson
  I want the CRM to look for another person at a company whose only person is the wrong one or opted out
  So that the company is not lost, and only a person I accepted gets mail

  Data: the stack runs django-prospecting with the fixed search provider (`PROSPECTING_SEARCH_PROVIDER = "fixed"`:
  the same three people for every company — Ewa Zielińska, Head of E-commerce; Marek Wójcik, Office Manager, whose
  role never fits; Tomasz Lis, CEO, whose employment is never confirmed — and the published address jan.nowak@ that
  gives the pattern first.last@) and the stub address tester (first.last@ exists). The worker consumes
  `prospecting_default`. Every scenario imports its own company with one contact, so none consumes the seed and the
  feature can be re-run on one database. Replies get their class through communicator's `test/ingest-reply/`.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And the channel clock is monday 10:00
    And the send counters of the reference week are cleared
    And the communicator channel is in "sandbox" mode

  Scenario: A wrong-person reply of the only person starts a search for another person
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "I left the company" with the class "wrong_person"
    Then the history of the company "company" says "looking for another person" for the reason "wrong_person"
    And the company "company" is not marked do not contact
    And the people search of the company "company" is done with the mail pattern "{first}.{last}"
    And the company "company" has 3 candidates waiting for review

  Scenario: Every candidate carries four checks, with "no information" after three tries
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "I left the company" with the class "wrong_person"
    Then the candidate "Zielińska" of the company "company" has every check "ok"
    And the candidate "Zielińska" of the company "company" has the address "ewa.zielinska@" at the company's domain
    And the candidate "Wójcik" of the company "company" has the check "role" "no_info" after 3 tries
    And the candidate "Lis" of the company "company" has the check "employed" "no_info" after 3 tries
    And every check "ok" of the candidates of the company "company" has a source and a date

  Scenario: A confirmed opt-out of the only person starts a search; only the person is blocked
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "Please take me off" with the class "unsubscribe"
    And the suspected opt-out of "company" is confirmed
    Then the history of the company "company" says "looking for another person" for the reason "opted_out"
    And the company "company" is not marked do not contact
    And the company "company" has 3 candidates waiting for review

  Scenario: Only an accepted candidate becomes a contact that may be mailed
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "I left the company" with the class "wrong_person"
    And the candidate "Zielińska" of the company "company" is accepted
    And the candidate "Wójcik" of the company "company" is rejected
    Then the company "company" has a contact "ewa.zielinska@" with the source "prospecting" and no mail block
    And the company "company" has no contact with the local part "marek.wojcik@"
    And the candidate "Wójcik" of the company "company" is "rejected"
    And accepting the candidate "Zielińska" of the company "company" again is refused

  Scenario: A wrong-person reply gets a draft asking for the right person, approved like every draft
    Given a fresh company is imported as "company"
    And the company "company" is contacted with the static mail "reply.thanks"
    When the contact of "company" replies "I left the company" with the class "wrong_person"
    Then the review queue has a referral request to the contact of "company"
    And approving the referral request of "company" succeeds
