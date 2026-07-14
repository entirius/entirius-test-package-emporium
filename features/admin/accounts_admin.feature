@admin @accounts @v2
Feature: Accounts Admin API v2
  As an admin user
  I want to view customer accounts via the admin API
  So that I can support customers and review account data

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  # --- Authentication: Customers ---

  Scenario: Unauthenticated request to customers returns 401
    When I GET the v2 admin endpoint "accounts/admin/customers/" without auth
    Then the response status should be 401

  Scenario: Non-admin user on customers returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "accounts/admin/customers/"
    Then the response status should be 403

  Scenario: Admin user can list customers
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/customers/"
    Then the response status should be 200

  # --- Authentication: Groups ---

  Scenario: Unauthenticated request to groups returns 401
    When I GET the v2 admin endpoint "accounts/admin/groups/" without auth
    Then the response status should be 401

  Scenario: Admin user can list groups
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/groups/"
    Then the response status should be 200

  # --- Authentication: Channels ---

  Scenario: Unauthenticated request to channels returns 401
    When I GET the v2 admin endpoint "accounts/admin/channels/" without auth
    Then the response status should be 401

  Scenario: Admin user can list channels
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/channels/"
    Then the response status should be 200

  # --- Customer List ---

  Scenario: Customer list returns paginated structure
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/customers/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Customer list contains fixture data
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/customers/"
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: Customer list search by name
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/customers/" with params
      | param  | value     |
      | search | kowalski  |
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: Customer list filter by group
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/customers/" with params
      | param | value |
      | group | b2b   |
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: Customer list filter by channel
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/customers/" with params
      | param          | value         |
      | source_channel | default-local |
    Then the response status should be 200

  Scenario: Customer list filter by active status
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/customers/" with params
      | param     | value |
      | is_active | true  |
    Then the response status should be 200

  Scenario: Customer list ordering
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/customers/" with params
      | param    | value |
      | ordering | email |
    Then the response status should be 200

  # --- Customer Detail ---

  Scenario: Customer detail returns full profile
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/customers/"
    Then the response status should be 200
    And I save the first result field "uid" as "saved.customer_uid"
    When I GET the v2 admin endpoint "accounts/admin/customers/{saved.customer_uid}/"
    Then the response status should be 200
    And the response should have the fields
      | field               |
      | uid                 |
      | email               |
      | firstname           |
      | lastname            |
      | is_active           |
      | is_verified         |
      | addresses           |
      | addresses_count     |
      | wishlist_items_count|
      | created_at          |
      | updated_at          |

  # --- Groups ---

  Scenario: Groups list contains fixture groups
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/groups/"
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "code" equal to "b2b"

  # --- Channels ---

  Scenario: Channels list contains fixture channels
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "accounts/admin/channels/"
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "idx" equal to "default-local"
