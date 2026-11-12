@stock-alerts
Feature: Back-in-stock alerts
  As a shopper who found my size sold out
  I want one e-mail when it is back
  So that I can buy it before it sells out again

  Data: ENT-CFG01 (Captain's Living Room Set) has the sold-out variant ENT-S004 and the variant ENT-S001 in stock
  (package/qty.csv). A scenario raises ENT-S004 in the channel's manual warehouse through the QMS admin API, the path
  real imports use, and sets it back to 0 at the end; the Background does it too, after a failed run. The check runs
  through the service shell, not from beat; zeno runs it with STOCK_ALERTS_WAVE_FACTOR = 2. Every scenario uses its own
  address and starts with an empty mailbox and no waiting request for ENT-S004, so the feature is re-runnable.

  Background:
    Given the channel is the primary channel
    And the sandbox mailbox is empty
    And no back-in-stock request waits for the sold-out variant

  Scenario: SA-1 a request for a sold-out size is saved and confirmed by e-mail
    When "bdd-sa-signup@example.com" asks for an alert on the sold-out variant
    Then the response status should be 201
    And the response field "status" should equal "saved"
    And "bdd-sa-signup@example.com" receives 1 back-in-stock e-mail
    And the newest back-in-stock e-mail of "bdd-sa-signup@example.com" names the product and has a cancel link

  Scenario: SA-2 the same request again keeps one waiting request and sends no second e-mail
    When "bdd-sa-repeat@example.com" asks for an alert on the sold-out variant
    And "bdd-sa-repeat@example.com" asks for an alert on the sold-out variant
    Then the response status should be 201
    And the response field "status" should equal "saved"
    And 1 back-in-stock request of "bdd-sa-repeat@example.com" is waiting
    And "bdd-sa-repeat@example.com" receives 1 back-in-stock e-mail
    And "bdd-sa-repeat@example.com" receives no further back-in-stock e-mail

  Scenario: SA-3 a size in stock cannot be asked for
    When "bdd-sa-instock@example.com" asks for an alert on the in-stock variant
    Then the response status should be 409
    And the error response should have error code "IN_STOCK"

  Scenario: SA-4 a filled honeypot answers like a saved request and stores nothing
    When "bdd-sa-bot@example.com" asks for an alert on the sold-out variant with the honeypot filled
    Then the response status should be 201
    And the response field "status" should equal "saved"
    And 0 back-in-stock requests of "bdd-sa-bot@example.com" are waiting
    And "bdd-sa-bot@example.com" receives no further back-in-stock e-mail

  Scenario: SA-5 a restock sends one alert with the size and a link to it
    Given "bdd-sa-restock@example.com" waits for the sold-out variant
    When the sold-out variant gets 1 piece in the manual warehouse
    And the restock check runs
    Then "bdd-sa-restock@example.com" receives 2 back-in-stock e-mails
    And the newest back-in-stock e-mail of "bdd-sa-restock@example.com" names the size and links to the variant
    When the restock check runs
    Then "bdd-sa-restock@example.com" receives no further back-in-stock e-mail
    And the sold-out variant is sold out again

  Scenario: SA-6 fewer pieces than people: the alerts go out in waves, oldest request first
    Given "bdd-sa-wave-1@example.com" waits for the sold-out variant
    And "bdd-sa-wave-2@example.com" waits for the sold-out variant
    And "bdd-sa-wave-3@example.com" waits for the sold-out variant
    When the sold-out variant gets 1 piece in the manual warehouse
    And the restock check runs
    Then "bdd-sa-wave-1@example.com" receives 2 back-in-stock e-mails
    And "bdd-sa-wave-2@example.com" receives 2 back-in-stock e-mails
    And "bdd-sa-wave-3@example.com" receives no further back-in-stock e-mail
    When the restock check runs
    Then "bdd-sa-wave-3@example.com" receives 2 back-in-stock e-mails
    And the sold-out variant is sold out again

  Scenario: SA-7 a request cancelled by the link of its e-mail gets no alert
    Given "bdd-sa-cancel@example.com" waits for the sold-out variant
    When "bdd-sa-cancel@example.com" cancels by the link of the signup e-mail
    Then the response status should be 200
    And the response field "status" should equal "cancelled"
    And the back-in-stock request of "bdd-sa-cancel@example.com" is "cancelled"
    When the sold-out variant gets 1 piece in the manual warehouse
    And the restock check runs
    Then "bdd-sa-cancel@example.com" receives no further back-in-stock e-mail
    And the sold-out variant is sold out again

  @module-checkout
  Scenario: SA-8 a piece back from a cancelled order sends the alert
    Given the sold-out variant gets 1 piece in the manual warehouse
    And a guest order reserves the piece of the sold-out variant
    And "bdd-sa-order@example.com" waits for the sold-out variant
    When the restock check runs
    Then "bdd-sa-order@example.com" receives no further back-in-stock e-mail
    When the guest order is cancelled
    And the restock check runs
    Then "bdd-sa-order@example.com" receives 2 back-in-stock e-mails
    And the sold-out variant is sold out again

  Scenario: SA-9 the demand lists the waiting variant; a viewer cannot cancel a request
    Given "bdd-sa-demand@example.com" waits for the sold-out variant
    And I am authenticated as an admin user
    When I GET the v2 admin endpoint "stock-alerts/admin/{channel_idx}/demand/?search=ENT-S004"
    Then the response status should be 200
    And the demand row of the sold-out variant counts 1 waiting request
    Given I am authenticated as the viewer staff user
    When I GET the v2 admin endpoint "stock-alerts/admin/{channel_idx}/subscriptions/?sku=ENT-S004&status=waiting"
    Then the response status should be 200
    When the viewer cancels the back-in-stock request of "bdd-sa-demand@example.com"
    Then the response status should be 403

  @module-leads
  Scenario: SA-10 a GDPR erasure cancels the request and anonymises it
    Given "bdd-sa-erase@example.com" waits for the sold-out variant
    And I am authenticated as an admin user
    When I POST to the v2 admin endpoint "leads/admin/gdpr/erase/" with body
      """
      {"email": "bdd-sa-erase@example.com"}
      """
    Then the response status should be 200
    And the saved back-in-stock request is cancelled with the reason "erased" and holds no address

  @module-agreements
  Scenario: SA-11 the consent of a request shows in agreements, its cancel as a withdrawal
    Given "bdd-sa-consent@example.com" waits for the sold-out variant
    Then the consent "stock-alerts" of "bdd-sa-consent@example.com" is "granted" in agreements
    When "bdd-sa-consent@example.com" cancels by the link of the signup e-mail
    Then the response status should be 200
    And the consent "stock-alerts" of "bdd-sa-consent@example.com" is "withdrawn" in agreements
