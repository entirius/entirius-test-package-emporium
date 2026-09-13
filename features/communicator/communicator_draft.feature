@communicator
Feature: Communicator — templates, communicate() and the review queue
  As a module that needs to write to a lead
  I want one call to return a message by template key, and a human to review AI drafts
  So that nothing leaves without the right template, footer and approval

  Data: fixtures/django_communicator.cfg.yaml (channel default-europe in sandbox mode; templates
  lead.cold.shop and lead.cold.b2b as AI prompts on fake-chat, followup static + auto_approve;
  suppressed blocked@example-shop-9.test and domain example-blocked.test). Needs the toolbox up with
  fake models (make toolbox-check). communicate() is called through the development endpoint
  test/communicate/. `attempts` counts the toolbox calls made for a message: 0 means the toolbox was
  never reached. Every scenario uses its own subject_ref and re-runs on one seed.

  Background:
    Given I am authenticated as an admin user

  Scenario: C-01 an AI template creates a draft waiting for review
    When I request the "lead.cold.shop" message for "jan@example-shop-1.test" about "bdd:c-01"
    Then the response field "status" should equal "review_required"
    And the response field "model" should not be empty
    And the response field "rendered_prompt" should contain "Firma: Example Shop 1"
    And the response field "subject" should not be empty
    And the response field "attempts" should equal integer 1
    And the nested response field "template.key" should equal "lead.cold.shop"
    And the nested response field "usage.input_tokens" should not equal "0"

  Scenario: C-02 a static auto-approve template is approved without the toolbox
    When I request the "followup" message for "jan@example-shop-1.test" about "bdd:c-02" without review
    Then the response field "status" should equal "approved"
    And the response field "subject" should equal "Re: Example Shop 1"
    And the response field "attempts" should equal integer 0
    And the response field "model" should be empty

  Scenario: C-06 a suppressed email or domain never reaches the toolbox
    When I request the "lead.cold.shop" message for "blocked@example-shop-9.test" about "bdd:c-06"
    Then the response field "status" should equal "suppressed"
    And the response field "attempts" should equal integer 0
    When I request the "lead.cold.shop" message for "owner@www.example-blocked.test" about "bdd:c-06"
    Then the response field "status" should equal "suppressed"
    And the response field "attempts" should equal integer 0

  Scenario: C-07 accept stamps the reviewer and cannot be repeated
    When I request the "lead.cold.shop" message for "jan@example-shop-1.test" about "bdd:c-07"
    Then I save the response field "id" as "saved.c07"
    When I accept the message "saved.c07"
    Then the response status should be 200
    And the response field "status" should equal "approved"
    And the response field "reviewed_by_id" should not be null
    And the response field "reviewed_at" should not be null
    When I accept the message "saved.c07"
    Then the response status should be 409

  Scenario: C-08 rewrite with notes creates the next version and supersedes the draft
    When I request the "lead.cold.shop" message for "jan@example-shop-1.test" about "bdd:c-08"
    Then I save the response field "id" as "saved.c08"
    When I rewrite the message "saved.c08" with body
      """
      {"notes": "Wspomnij o szybkości wersji mobilnej."}
      """
    Then the response status should be 201
    And the response field "version" should equal integer 2
    And the response field "parent_id" should equal "{saved.c08}"
    And the response field "review_notes" should equal "Wspomnij o szybkości wersji mobilnej."
    And the response field "rendered_prompt" should contain "Wspomnij o szybkości wersji mobilnej."
    When I accept the message "saved.c08"
    Then the response status should be 409

  Scenario: C-09 a manual edit is a human version without a toolbox call
    When I request the "lead.cold.shop" message for "jan@example-shop-1.test" about "bdd:c-09"
    Then I save the response field "id" as "saved.c09"
    When I edit the message "saved.c09" with body
      """
      {"subject": "Pytanie o sklep", "body_text": "Dzień dobry,\n\nnapisane ręcznie."}
      """
    Then the response status should be 201
    And the response field "edited_by_human" should be true
    And the response field "version" should equal integer 2
    And the response field "attempts" should equal integer 0
    And the response field "subject" should equal "Pytanie o sklep"

  Scenario: C-29 editing a template keeps existing drafts on their version
    When I request the "lead.cold.b2b" message for "anna@example-shop-2.test" about "bdd:c-29"
    Then I save the response field "id" as "saved.c29_old"
    And I save the nested response field "template.version_id" as "saved.c29_old_version"
    And I save the template id of "lead.cold.b2b" as "saved.c29_template"
    When I append a unique sentence to the body of template "saved.c29_template"
    Then the response status should be 200
    When I request the "lead.cold.b2b" message for "anna@example-shop-2.test" about "bdd:c-29-new"
    Then the nested response field "template.version_id" should not equal "{saved.c29_old_version}"
    And the response field "rendered_prompt" should contain "BDD C-29 revision"
    And the message "saved.c29_old" in the "review_required" queue uses template version "saved.c29_old_version"
