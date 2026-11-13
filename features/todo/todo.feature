@todo @crm @crm-core
Feature: Tasks — a person's to-dos with a due date about any object
  As a salesperson
  I want tasks with a due date, one list for today, and a task I can close, cancel or reopen
  So that nothing I promised falls through

  Data: none seeded. Every task is about its own `bdd:todo:<run>` subject, so the feature can be re-run on one
  database; tasks are never deleted (a mistake is cancelled).

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And a run-unique suffix is saved as "run"
    And the open tasks about "bdd:todo:{run}" are cancelled when the scenario ends

  Scenario: A task is created, edited, done and reopened
    When I POST to the v2 admin endpoint "todo/admin/{channel_idx}/tasks/" with body
      """
      {"subject_ref": "bdd:todo:{run}", "subject_label": "BDD subject", "title": "BDD write the offer", "kind": "mail"}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.task"
    And the response field "status" should equal "open"
    And the response field "source" should equal "manual"
    When I PATCH the v2 admin endpoint "todo/admin/{channel_idx}/tasks/{saved.task}/" with body
      """
      {"title": "BDD write the offer today"}
      """
    Then the response field "title" should equal "BDD write the offer today"
    When I POST to the v2 admin endpoint "todo/admin/{channel_idx}/tasks/{saved.task}/done/" with body
      """
      {"outcome": "sent"}
      """
    Then the response field "status" should equal "done"
    And the response field "outcome" should equal "sent"
    When I POST to the v2 admin endpoint "todo/admin/{channel_idx}/tasks/{saved.task}/done/" with body
      """
      {"outcome": "again"}
      """
    Then the response status should be 409
    When I POST to the v2 admin endpoint "todo/admin/{channel_idx}/tasks/{saved.task}/reopen/" with body
      """
      {}
      """
    Then the response field "status" should equal "open"

  Scenario: A cancelled task keeps its reason and a task is never deleted
    When I POST to the v2 admin endpoint "todo/admin/{channel_idx}/tasks/" with body
      """
      {"subject_ref": "bdd:todo:{run}", "title": "BDD mistake"}
      """
    Then I save the response field "id" as "saved.task"
    When I POST to the v2 admin endpoint "todo/admin/{channel_idx}/tasks/{saved.task}/cancel/" with body
      """
      {"reason": "created by mistake"}
      """
    Then the response field "status" should equal "cancelled"
    And the response field "outcome" should equal "created by mistake"
    When I DELETE the v2 admin endpoint "todo/admin/{channel_idx}/tasks/{saved.task}/"
    Then the response status should be 405

  Scenario: A task due yesterday is on the caller's today list as overdue
    When I POST to the v2 admin endpoint "todo/admin/{channel_idx}/tasks/" with body
      """
      {"subject_ref": "bdd:todo:{run}", "title": "BDD overdue", "due_at": "2026-01-01T09:00:00+00:00"}
      """
    Then I save the response field "id" as "saved.task"
    When I GET the v2 admin endpoint "todo/admin/{channel_idx}/today/"
    Then the response status should be 200
    And the results hold the saved id "saved.task"
    And the response field "overdue" should not equal "0"

  Scenario: The task list filters by subject and status
    When I POST to the v2 admin endpoint "todo/admin/{channel_idx}/tasks/" with body
      """
      {"subject_ref": "bdd:todo:{run}", "title": "BDD filtered"}
      """
    And I GET the v2 admin endpoint "todo/admin/{channel_idx}/tasks/?subject_ref=bdd:todo:{run}&status=open"
    Then the response status should be 200
    And the response field "count" should equal integer 1

  Scenario: A due date without an offset is refused
    When I POST to the v2 admin endpoint "todo/admin/{channel_idx}/tasks/" with body
      """
      {"subject_ref": "bdd:todo:{run}", "title": "BDD naive", "due_at": "2026-01-01T09:00:00"}
      """
    Then the response status should be 400
