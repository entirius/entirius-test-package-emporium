@leads @todo @crm @crm-history
Feature: CRM history — the journal of every change, cancelled tasks and the task dialog's company picker
  As a sales manager
  I want one journal of who did what, when, on what and why, cancelled tasks with their reason and author,
  and my own companies first when I add a task
  So that I can rebuild any day of the team without looking through every screen

  Data: the seed's staff users `manager` and `editor` (scripts/seed-crm.py). Every scenario imports its own company
  with a unique domain; the channel setting a scenario changes is put back when it ends, so `make bdd TAGS=@crm` can
  be re-run on one database (the history only grows).

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  # U5: the reason and the author of a cancelled task reach the history and the cancelled list
  Scenario: A task cancelled with a reason keeps the reason and who cancelled it
    Given a fresh company owned by the manager staff user is imported as "company"
    When a phone task "Call the owner" due now is created about the company "company" for the manager staff user
    And the manager staff user cancels the task of the company "company" with the reason "duplicate"
    Then the company "company" has an activity "task" containing "cancelled: Call the owner"
    And the history entry "task_cancelled" of the company "company" has the reason "duplicate" by the manager staff user
    And the task of the company "company" is in the cancelled tasks of the manager staff user with the reason "duplicate"

  # U6: Add task from Today — the caller's companies first
  Scenario: The company list puts the caller's own companies first
    Given a fresh company owned by the editor staff user is imported as "company"
    Then the editor staff user's company list with "mine first" starts with their own companies

  # U11: the journal of the channel, filtered by person, day, kind and company
  Scenario: The history lists a person's actions of the day, filtered by kind and company
    Given a fresh company owned by the manager staff user is imported as "company"
    When a phone task "Send the offer" due now is created about the company "company" for the manager staff user
    And the manager staff user cancels the task of the company "company" with the reason "sent by mail"
    Then the history of today filtered by the manager staff user and the kind "task" names the company "company"
    And the history filtered by the company "company" has only entries of that company
    And the manager staff user is among the people of the history

  Scenario: A change of the channel settings is in the history with the old and the new value
    When the days until a "not now" company comes back are changed for this scenario
    Then the history has a settings entry by the admin user with the old and the new days
