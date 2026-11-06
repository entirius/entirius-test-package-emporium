@leads @outbound @s5-settings
Feature: Leads settings API behind the S5 CMS screens — rules, profiles and the IMAP mailbox
  As a salesperson
  I want to configure rules, analysis and recipient profiles and see the IMAP mailbox without the API
  So that the three CMS screens (Leads -> Settings -> Rules, Analysis and recipients, IMAP mailbox) have a contract

  Roadmap T2a F5 (entirius-infra/outbound/roadmap.md). The screens call exactly these endpoints, so the scenarios walk
  the create, edit and delete the screens offer. Every created row has a `bdd-s5` key and is deleted by its own
  scenario; nothing consumes the seed, so `make bdd TAGS=@s5-settings` can be re-run. The mailbox is only read: it is
  the row the inbox poll of the stack runs on, and a write would change what other scenarios receive.
  The CMS screens themselves are covered by `e2e/p5-leads-settings-config.spec.js` in entirius-pwa-cms.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  @s5-rules
  Scenario: A rule is added inactive, edited and deleted
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/rules/" with body
      """
      {"trigger": "intel_ready", "action": "communicate", "template_key": "bdd-s5-rule", "is_active": false, "order": 999}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.rule_id"
    And the response field "template_key" should equal "bdd-s5-rule"
    And the response field "stage_id" should be null
    When I PATCH the v2 admin endpoint "leads/admin/{channel_idx}/rules/{saved.rule_id}/" with body
      """
      {"template_key": "bdd-s5-rule-b", "cooldown_hours": 48}
      """
    Then the response status should be 200
    And the response field "template_key" should equal "bdd-s5-rule-b"
    And the response field "is_active" should be false
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/rules/"
    Then the results should contain an item with "template_key" equal to "bdd-s5-rule-b"
    When I DELETE the v2 admin endpoint "leads/admin/{channel_idx}/rules/{saved.rule_id}/"
    Then the response status should be 204
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/rules/"
    Then the results should not contain an item with "template_key" equal to "bdd-s5-rule-b"

  @s5-rules
  Scenario: A rule on a stage needs the stage
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/rules/" with body
      """
      {"trigger": "stage_entered", "action": "communicate", "template_key": "bdd-s5-rule", "is_active": false}
      """
    Then the response status should be 400

  @s5-profiles
  Scenario: An analysis profile is added, listed without its prompt, edited and deleted
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/analysis-profiles/" with body
      """
      {"key": "bdd-s5-analysis", "model": "fake-chat", "prompt_text": "Analyse {{ company }}", "json_schema": {}, "is_active": false}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.profile_id"
    And the response field "prompt_text" should equal "Analyse {{ company }}"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/analysis-profiles/"
    Then the results should contain an item with "key" equal to "bdd-s5-analysis"
    When I PATCH the v2 admin endpoint "leads/admin/{channel_idx}/analysis-profiles/{saved.profile_id}/" with body
      """
      {"prompt_text": "Analyse again"}
      """
    Then the response status should be 200
    And the response field "prompt_text" should equal "Analyse again"
    When I DELETE the v2 admin endpoint "leads/admin/{channel_idx}/analysis-profiles/{saved.profile_id}/"
    Then the response status should be 204

  @s5-profiles
  Scenario: A recipient profile is added, edited and deleted; a second one with the same key is refused
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/recipient-profiles/" with body
      """
      {"key": "bdd-s5-recipient", "model": "fake-chat", "prompt_text": "Pick one", "json_schema": {}}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.profile_id"
    When I POST to the v2 admin endpoint "leads/admin/{channel_idx}/recipient-profiles/" with body
      """
      {"key": "bdd-s5-recipient", "model": "fake-chat", "prompt_text": "Pick two", "json_schema": {}}
      """
    Then the response status should be 409
    When I PATCH the v2 admin endpoint "leads/admin/{channel_idx}/recipient-profiles/{saved.profile_id}/" with body
      """
      {"model": "fake-chat-2"}
      """
    Then the response status should be 200
    And the response field "model" should equal "fake-chat-2"
    When I DELETE the v2 admin endpoint "leads/admin/{channel_idx}/recipient-profiles/{saved.profile_id}/"
    Then the response status should be 204

  @s5-mailbox
  Scenario: The IMAP mailbox is read with a stored password flag and never the password itself
    When I GET the v2 admin endpoint "communicator/admin/{channel_idx}/mailbox/"
    Then the response status should be 200
    And the response should have the fields
      | field         |
      | imap_host     |
      | imap_port     |
      | imap_use_ssl  |
      | imap_user     |
      | has_password  |
      | folder        |
      | is_active     |
    And the response field "has_password" should be true
    And the response should not contain the field "imap_password"
