@admin @email-admin @v2
Feature: Email Admin API v2
  As an admin user
  I want to manage email configuration via API
  So that CMS can display and edit email content

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  # --- Authentication ---

  Scenario: Unauthenticated request to channels returns 401
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/" without auth
    Then the response status should be 401

  Scenario: Non-admin user on channels returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/"
    Then the response status should be 403

  Scenario: Admin user can access channels
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/"
    Then the response status should be 200

  Scenario: Unauthenticated request returns structured error
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/" without auth
    Then the response status should be 401
    And the error response should have error code "AUTHENTICATION_REQUIRED"
    And the error response should have a debug_id

  Scenario: Non-admin request returns structured error
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/"
    Then the response status should be 403
    And the error response should have error code "PERMISSION_DENIED"
    And the error response should have a debug_id

  # --- Channel List ---

  Scenario: List email channels returns paginated structure
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: List email channels returns fixture channel
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/"
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "idx" equal to "default-europe"

  Scenario: List channels respects page_size parameter
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/" with params
      | param     | value |
      | page_size | 1     |
    Then the response status should be 200
    And the results should contain at most 1 items

  # --- Channel Retrieve ---

  Scenario: Retrieve email channel by pk
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "email/admin/{channel_idx}/channels/1/" with body
      """
      {"main_background_color": "#FFFFFF"}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/1/"
    Then the response status should be 200
    And the response field "idx" should equal "default-europe"
    And the response field "label" should equal "Default Europe"
    And the response field "main_background_color" should equal "#FFFFFF"

  Scenario: Retrieve non-existent channel returns 404
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/999999/"
    Then the response status should be 404

  # --- Channel Update ---

  Scenario: Update channel branding color
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "email/admin/{channel_idx}/channels/1/" with body
      """
      {"main_background_color": "#F5F5F5"}
      """
    Then the response status should be 200
    And the response field "main_background_color" should equal "#F5F5F5"

  Scenario: Update channel sender info
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "email/admin/{channel_idx}/channels/1/" with body
      """
      {"from_name": "Updated Store", "from_email": "updated@test.entirius.com"}
      """
    Then the response status should be 200
    And the response field "from_name" should equal "Updated Store"
    And the response field "from_email" should equal "updated@test.entirius.com"

  # --- Channel No DELETE ---

  Scenario: DELETE on channel returns 405
    Given I am authenticated as an admin user
    When I DELETE the v2 admin endpoint "email/admin/{channel_idx}/channels/1/"
    Then the response status should be 405

  # --- LangChannelConfig List ---

  Scenario: List lang configs for channel returns paginated structure
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/1/lang-configs/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: List lang configs contains fixture records
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/channels/1/lang-configs/"
    Then the response status should be 200
    And the results count should be greater than 0

  # --- LangChannelConfig Retrieve ---

  Scenario: Retrieve lang config by pk
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/lang-configs/1/"
    Then the response status should be 200
    And the response field "channel_id" should equal integer 1
    And the response field "shop_name" should equal "Entirius Store"

  Scenario: Retrieve non-existent lang config returns 404
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/lang-configs/999999/"
    Then the response status should be 404

  # --- LangChannelConfig Update ---

  Scenario: Update lang config footer copy
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "email/admin/{channel_idx}/lang-configs/1/" with body
      """
      {"footer_copy": "BDD updated footer text"}
      """
    Then the response status should be 200
    And the response field "footer_copy" should equal "BDD updated footer text"

  Scenario: Update lang config social links
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "email/admin/{channel_idx}/lang-configs/1/" with body
      """
      {"footer_link_facebook": "https://facebook.com/bdd-test"}
      """
    Then the response status should be 200
    And the response field "footer_link_facebook" should equal "https://facebook.com/bdd-test"

  # --- LangChannelConfig No DELETE ---

  Scenario: DELETE on lang config returns 405
    Given I am authenticated as an admin user
    When I DELETE the v2 admin endpoint "email/admin/{channel_idx}/lang-configs/1/"
    Then the response status should be 405

  # --- Templates List ---

  Scenario: List accounts-new-account templates returns paginated structure
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/templates/accounts-new-account/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: List templates for unknown type returns 404
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/templates/unknown-type/"
    Then the response status should be 404

  # --- Template Retrieve ---

  Scenario: Retrieve accounts-new-account template with custom values
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "email/admin/{channel_idx}/templates/accounts-new-account/2/" with body
      """
      {"subject": "Custom Welcome Subject", "welcome": "Welcome to our store!"}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/templates/accounts-new-account/2/"
    Then the response status should be 200
    And the response field "subject" should equal "Custom Welcome Subject"
    And the response field "welcome" should equal "Welcome to our store!"

  Scenario: Retrieve template with null values returns null fields
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/templates/accounts-new-account/1/"
    Then the response status should be 200
    And the response field "subject" should be null
    And the response field "welcome" should be null

  Scenario: Retrieve non-existent template returns 404
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "email/admin/{channel_idx}/templates/accounts-new-account/999999/"
    Then the response status should be 404

  # --- Template Update ---

  Scenario: Update template subject and welcome text
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "email/admin/{channel_idx}/templates/accounts-new-account/2/" with body
      """
      {"subject": "BDD Updated Subject", "welcome": "Hello from BDD!"}
      """
    Then the response status should be 200
    And the response field "subject" should equal "BDD Updated Subject"
    And the response field "welcome" should equal "Hello from BDD!"

  Scenario: Update template to clear a field with null
    Given I am authenticated as an admin user
    When I PATCH the v2 admin endpoint "email/admin/{channel_idx}/templates/accounts-new-account/2/" with body
      """
      {"announce": null}
      """
    Then the response status should be 200
    And the response field "announce" should be null

  # --- Template No DELETE ---

  Scenario: DELETE on template returns 405
    Given I am authenticated as an admin user
    When I DELETE the v2 admin endpoint "email/admin/{channel_idx}/templates/accounts-new-account/1/"
    Then the response status should be 405
