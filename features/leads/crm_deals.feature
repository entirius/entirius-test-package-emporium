@leads @crm @crm-deals
Feature: CRM deals — a sales pipeline on a company
  As a salesperson
  I want to open a deal on a company, move it along the pipeline and close it as won or lost
  So that I see what I am selling and what it is worth

  Data: the seed's sales pipeline (scripts/seed-crm.py): qualified, proposal, negotiation (open), won, lost, and the
  channel's default currency PLN. Every scenario opens its deal on a company it imports itself; the board totals are
  compared before and after, so `make bdd TAGS=@crm` can be re-run on one database.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user
    And a fresh company is imported as "company"

  Scenario: A deal opens in the first open stage in the channel's currency
    When a deal "BDD shop rollout" worth "1200.00" is opened on the company "company"
    Then the response status should be 201
    And the nested response field "stage.key" should equal "qualified"
    And the response field "currency" should equal "PLN"
    And the response field "value_one_off" should equal "1200.00"
    And the company "company" has an activity "deal" containing "deal opened: BDD shop rollout"

  Scenario: A deal moves to the next stage and its history says so
    Given a deal "BDD move" worth "500.00" is opened on the company "company"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/transition/" with body
      """
      {"stage_key": "proposal"}
      """
    Then the response status should be 200
    And the nested response field "stage.key" should equal "proposal"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/activities/"
    Then the response field "results" should have at least one item with "message"

  Scenario: A lost deal needs a reason
    Given a deal "BDD lost" worth "300.00" is opened on the company "company"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/transition/" with body
      """
      {"kind": "lost"}
      """
    Then the response status should be 400
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/transition/" with body
      """
      {"kind": "lost", "lost_reason": "chose another vendor"}
      """
    Then the response status should be 200
    And the nested response field "stage.kind" should equal "lost"
    And the response field "closed_at" should not be null

  Scenario: A won deal is closed and cannot be deleted
    Given a deal "BDD won" worth "800.00" is opened on the company "company"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/transition/" with body
      """
      {"kind": "won"}
      """
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/"
    Then the response status should be 409

  Scenario: The board totals a stage per currency
    Given the board totals are remembered
    When a deal "BDD euro" worth "1000.00" is opened in "EUR" on the company "company"
    And a deal "BDD zloty" worth "250.50" is opened on the company "company"
    Then the board total of the stage "qualified" grew by "1000.00" in "EUR" and "250.50" in "PLN"
    And the board count of the stage "qualified" grew by 2

  Scenario: A deal without a currency on a value is refused
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/" with body
      """
      {"company_id": {company}, "title": "BDD bad value", "value_one_off": 100}
      """
    Then the response status should be 400

  Scenario: The deals of a company are listed on the company
    Given a deal "BDD listed" worth "10.00" is opened on the company "company"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/{company}/deals/"
    Then the response status should be 200
    And the item with "title" equal to "BDD listed" should exist
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/{company}/"
    Then the nested response field "deals.open" should equal "1"

  Scenario: A closed deal is archived out of the lists and the board, and restored
    Given a deal "BDD archived" worth "700.00" is opened on the company "company"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/archive/" with body
      """
      {}
      """
    Then the response status should be 409
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/transition/" with body
      """
      {"kind": "won"}
      """
    Then the response status should be 200
    Given the board totals are remembered
    And I am authenticated as the viewer staff user
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/archive/" with body
      """
      {}
      """
    Then the response status should be 403
    Given I am authenticated as an admin user
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/archive/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "archived_at" should not be null
    And the board count of the stage "won" grew by -1
    And the company "company" has an activity "deal" containing "deal archived: BDD archived"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/{company}/deals/"
    Then the results should not contain an item with "title" equal to "BDD archived"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/deals/?company={company}&archived=true"
    Then the item with "title" equal to "BDD archived" should exist
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/transition/" with body
      """
      {"kind": "open"}
      """
    Then the response status should be 409
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/deals/{deal}/restore/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "archived_at" should be null
    And the board count of the stage "won" grew by 0
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/{company}/deals/"
    Then the item with "title" equal to "BDD archived" should exist
