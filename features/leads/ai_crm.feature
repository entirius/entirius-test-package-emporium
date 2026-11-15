@leads @todo @ai-crm @module-ai_crm
Feature: AI CRM — an agent leads the salesperson through the day and updates the CRM (U10)
  As a salesperson
  I want one list of today's work and to tell an agent what I did
  So that the CRM is filled in for me — and nothing irreversible happens without my yes

  Data: the seed's staff users `manager`, `editor` and `viewer` (scripts/seed-access.py), the sales pipeline with the
  lost stage `lost` (scripts/seed-crm.py). Every scenario imports its own company; the import cancels the tasks
  it leaves open when the scenario ends, so `make bdd TAGS=@ai-crm` can be re-run on one database. The day plan and the
  today list are read in UTC and cut at 50 rows, oldest first: a manager with 50 older open tasks (a crm-walk-data
  run) pushes the scenario's task off both. The agent's short commands need no model, so the scenarios pass with the
  fake toolbox and with `AI_TOOLBOX_ENABLED=0`.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And a fresh company owned by the manager staff user is imported as "company"
    When a phone task "Call the buyer" due now is created about the company "company" for the manager staff user

  Scenario: The day plan of AI CRM is the same work as Today
    When the manager staff user asks the AI CRM agent for the day plan
    Then the AI CRM day plan lists the task of the company "company"
    And the AI CRM day plan holds the same tasks as the today list of the manager staff user

  Scenario: "Done" in the CMS conversation closes the task and the History names AI CRM
    When the manager staff user says to the AI CRM agent from the CMS "done #{company.task}: talked, sending an offer"
    Then the AI CRM agent answered without a refusal
    And the task of the company "company" is done by the manager staff user via ai-crm "cms"
    And the company "company" has an activity "task" by the manager staff user via ai-crm "cms"
    When the manager staff user says to the AI CRM agent from the CMS "note #{company}: wants the offer by Friday"
    Then the company "company" has an activity "note" containing "wants the offer by Friday"
    And the company "company" has an activity "note" by the manager staff user via ai-crm "cms"

  Scenario: The same from a terminal over MCP with the salesperson's token
    When the manager staff user calls the AI CRM tool "close_task" over MCP with
      """
      {"task_id": {company.task}, "outcome": "booked a meeting"}
      """
    Then the MCP tool result is not an error
    And the task of the company "company" is done by the manager staff user via ai-crm "mcp"
    When the manager staff user calls the AI CRM tool "create_task" over MCP with
      """
      {"company_id": {company}, "title": "BDD meeting prep", "due": "tomorrow"}
      """
    Then the MCP tool result is not an error

  Scenario: The agent does not see another salesperson's work
    Given a fresh company owned by the editor staff user is imported as "foreign"
    When a phone task "Not yours" due now is created about the company "foreign" for the editor staff user
    And the manager staff user asks the AI CRM agent for the day plan
    Then the AI CRM day plan does not list the task of the company "foreign"
    When the manager staff user calls the AI CRM tool "close_task" over MCP with
      """
      {"task_id": {foreign.task}, "outcome": "not mine"}
      """
    Then the MCP tool result is the error "not_found"
    And the task of the company "foreign" is open

  Scenario: A lost deal is only proposed and runs after the salesperson's yes
    Given a deal "BDD AI CRM deal" worth "900.00" is opened on the company "company"
    When the manager staff user says to the AI CRM agent from the CMS "deal #{deal} -> lost: chose another vendor"
    Then the AI CRM agent proposes an action to confirm
    And the deal is in an open stage
    When the manager staff user says to the AI CRM agent from the CMS "yes"
    Then the deal is in the stage "lost"
    And the company "company" has an activity "deal" by the manager staff user via ai-crm "cms"

  Scenario: Do not contact waits for a yes and "no" drops it
    When the manager staff user says to the AI CRM agent from the CMS "dnc #{company}: asked to stop"
    Then the AI CRM agent proposes an action to confirm
    When the manager staff user says to the AI CRM agent from the CMS "no"
    Then the AI CRM agent dropped the proposal
    And the company "company" is not marked do not contact

  Scenario: A viewer reads the plan but never writes through the agent
    When the viewer staff user asks the AI CRM agent for the day plan
    And the viewer staff user calls the AI CRM tool "close_task" with
      """
      {"task_id": {company.task}, "outcome": "x"}
      """
    Then the AI CRM tool answered 403
    And the AI CRM tool refused for the missing permission
    And the task of the company "company" is open
