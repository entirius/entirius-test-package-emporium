@notifications
Feature: Notifications — in-app inbox and escalation
  As an operator of the leads platform
  I want every module's call for attention to show up in-app and escalate when nobody reads it
  So that nothing important waits unseen

  Data: fixtures/django_notifications.cfg.yaml (channel default-europe; high → email after 1 min,
  high → Google Chat after 2 min with a blank webhook). Needs GreenMail (zeno: make mail) and the
  worker consuming notifications_default. The clock is shifted through the development test endpoint.

  Background:
    Given the sandbox mailbox is empty
    And I am authenticated as an admin user
    When I POST to the v2 admin endpoint "notifications/admin/default-europe/notifications/read-all/" with body
      """
      {}
      """
    Then the response status should be 200

  Scenario: N-01 notify(high) is unread, counted and readable over the admin API
    When I POST to the v2 admin endpoint "notifications/admin/default-europe/test/notify/" with body
      """
      {"recipient_role": "sales", "severity": "high", "subject_ref": "bdd:n-01", "title": "BDD N-01 lead waits", "body": "Raised by the BDD suite."}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.n01"
    When I GET the v2 admin endpoint "notifications/admin/default-europe/notifications/unread-count/"
    Then the response field "unread" should equal integer 1
    When I GET the v2 admin endpoint "notifications/admin/default-europe/notifications/?unread=1"
    Then the notification results contain the title "BDD N-01 lead waits"
    When I POST to the v2 admin endpoint "notifications/admin/default-europe/notifications/{saved.n01}/read/" with body
      """
      {}
      """
    Then the response field "read_at" should not be null
    When I GET the v2 admin endpoint "notifications/admin/default-europe/notifications/unread-count/"
    Then the response field "unread" should equal integer 0

  Scenario: N-02 an unread high notification escalates by email, then chat, each once
    When I POST to the v2 admin endpoint "notifications/admin/default-europe/test/notify/" with body
      """
      {"recipient_role": "sales", "severity": "high", "subject_ref": "bdd:n-02", "title": "BDD N-02 escalation", "body": "Nobody read this."}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.n02"
    When I run the notifications escalation 3 minutes from now
    Then the response field "created" should equal integer 2
    And the notification "saved.n02" has deliveries
      | kind        | status  |
      | in_app      | sent    |
      | email       | sent    |
      | google_chat | skipped |
    And the sandbox mailbox contains 1 messages
    And the last sandbox message subject starts with "BDD N-02 escalation"
    When I run the notifications escalation 3 minutes from now
    Then the response field "created" should equal integer 0
