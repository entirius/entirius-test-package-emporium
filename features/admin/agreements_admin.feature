@admin @agreements @v2
Feature: Agreements Admin API v2
  As an admin user
  I want to manage agreement definitions and versions via the admin API
  So that I can configure consent agreements for the storefront

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  # --- Authentication (Definitions) ---

  Scenario: Unauthenticated request to definitions returns 401
    When I GET the v2 admin endpoint "agreements/admin/definitions/" without auth
    Then the response status should be 401

  Scenario: Non-admin user on definitions returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "agreements/admin/definitions/"
    Then the response status should be 403

  Scenario: Admin user can access definitions
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "agreements/admin/definitions/"
    Then the response status should be 200

  # --- Authentication (Channels) ---

  Scenario: Unauthenticated request to channels returns 401
    When I GET the v2 admin endpoint "agreements/admin/channels/" without auth
    Then the response status should be 401

  Scenario: Admin user can access channels
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "agreements/admin/channels/"
    Then the response status should be 200

  # --- Authentication (Consents) ---

  Scenario: Unauthenticated request to consents returns 401
    When I GET the v2 admin endpoint "agreements/admin/consents/" without auth
    Then the response status should be 401

  Scenario: Admin user can access consents
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "agreements/admin/consents/"
    Then the response status should be 200

  # --- Definitions List ---

  Scenario: Definitions list returns paginated structure
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "agreements/admin/definitions/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Definitions list contains fixture definitions
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "agreements/admin/definitions/"
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "slug" equal to "terms-of-service"
    And the results should contain an item with "slug" equal to "marketing-email"

  # --- Definitions Filter ---

  Scenario: Filter definitions by category
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "agreements/admin/definitions/?category=mandatory"
    Then the response status should be 200
    And the results should contain an item with "slug" equal to "terms-of-service"
    And the results should not contain an item with "slug" equal to "marketing-email"

  Scenario: Filter definitions by consent_channel
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "agreements/admin/definitions/?consent_channel=email"
    Then the response status should be 200
    And the results should contain an item with "slug" equal to "marketing-email"
    And the results should not contain an item with "slug" equal to "terms-of-service"

  # --- Channels ---

  Scenario: Channels list returns paginated structure
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "agreements/admin/channels/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |
