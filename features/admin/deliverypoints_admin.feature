@admin @deliverypoints @v2
Feature: Delivery Points Admin API v2
  As an admin user
  I want to manage delivery points and types via the admin API
  So that I can configure carrier and custom delivery locations

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  # --- Authentication (Types) ---

  Scenario: Unauthenticated request to types returns 401
    When I GET the v2 admin endpoint "deliverypoints/admin/types/" without auth
    Then the response status should be 401

  Scenario: Non-admin user on types returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "deliverypoints/admin/types/"
    Then the response status should be 403

  Scenario: Admin user can access types
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "deliverypoints/admin/types/"
    Then the response status should be 200

  # --- Authentication (Points) ---

  Scenario: Unauthenticated request to points returns 401
    When I GET the v2 admin endpoint "deliverypoints/admin/points/" without auth
    Then the response status should be 401

  Scenario: Non-admin user on points returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "deliverypoints/admin/points/"
    Then the response status should be 403

  Scenario: Admin user can access points
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "deliverypoints/admin/points/"
    Then the response status should be 200

  # --- Types List ---

  Scenario: Types list returns paginated structure
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "deliverypoints/admin/types/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Types list contains fixture types
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "deliverypoints/admin/types/"
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "code" equal to "inpost"
    And the results should contain an item with "code" equal to "dpd"
    And the results should contain an item with "code" equal to "showroom"

  Scenario: Types list respects page_size parameter
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "deliverypoints/admin/types/" with params
      | param     | value |
      | page_size | 3     |
    Then the response status should be 200
    And the results should contain at most 3 items

  # --- Points List ---

  Scenario: Points list returns paginated structure
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "deliverypoints/admin/points/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  # --- Error Response Structure ---

  Scenario: Unauthenticated types request returns structured error
    When I GET the v2 admin endpoint "deliverypoints/admin/types/" without auth
    Then the response status should be 401
    And the error response should have error code "AUTHENTICATION_REQUIRED"
    And the error response should have a debug_id

  Scenario: Non-admin types request returns structured error
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "deliverypoints/admin/types/"
    Then the response status should be 403
    And the error response should have error code "PERMISSION_DENIED"
    And the error response should have a debug_id
