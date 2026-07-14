@admin @qms @warehouse @v2
Feature: QMS Warehouse Admin API v2
  As an admin user
  I want to manage warehouses and stock via the admin API
  So that I can control physical warehouse inventory

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  # --- Authentication ---

  Scenario: Unauthenticated request returns 401
    When I GET the v2 admin endpoint "qms/admin/warehouses/" without auth
    Then the response status should be 401

  Scenario: Non-admin user returns 403
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "qms/admin/warehouses/"
    Then the response status should be 403

  Scenario: Admin user can access warehouses
    When I GET the v2 admin endpoint "qms/admin/warehouses/"
    Then the response status should be 200

  # --- Warehouse List ---

  Scenario: List returns fixture warehouses
    When I GET the v2 admin endpoint "qms/admin/warehouses/"
    Then the response status should be 200

  Scenario: Filter by is_active=true
    When I GET the v2 admin endpoint "qms/admin/warehouses/" with params
      | param       | value |
      | is_active | true  |
    Then the response status should be 200

  Scenario: Search by code
    When I GET the v2 admin endpoint "qms/admin/warehouses/" with params
      | param    | value  |
      | search | manual |
    Then the response status should be 200
    And the response should contain at least 1 items

  # --- Warehouse Detail ---

  Scenario: Retrieve warehouse by code
    When I GET the v2 admin endpoint "qms/admin/warehouses/wh-manual/"
    Then the response status should be 200
    And the response field "code" should equal "wh-manual"
    And the response field "source_type" should equal "manual"
    And the response field "is_active" should be true
    And the response field "channel_idxs" should be a list

  Scenario: Retrieve nonexistent warehouse returns 404
    When I GET the v2 admin endpoint "qms/admin/warehouses/nonexistent/"
    Then the response status should be 404

  # --- Stock List ---

  Scenario: List stock for manual warehouse
    When I GET the v2 admin endpoint "qms/admin/warehouses/wh-manual/stock/"
    Then the response status should be 200
    And the response field "results" should be a list

  Scenario: Search stock by SKU
    When I GET the v2 admin endpoint "qms/admin/warehouses/wh-manual/stock/" with params
      | param    | value   |
      | search | ENT-S001 |
    Then the response status should be 200
    And the response field "count" should equal integer 1

  # --- Bulk Stock Edit ---

  Scenario: Bulk edit creates and updates stock
    When I PATCH the v2 admin endpoint "qms/admin/warehouses/wh-manual/stock/edit/" with body
      """
      {"items": [{"sku": "BDD-QMS-001", "quantity": 42}]}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "qms/admin/warehouses/wh-manual/stock/" with params
      | param    | value       |
      | search | BDD-QMS-001 |
    Then the response status should be 200
    And the response field "count" should equal integer 1

  Scenario: Bulk edit rejects negative quantity
    When I PATCH the v2 admin endpoint "qms/admin/warehouses/wh-manual/stock/edit/" with body
      """
      {"items": [{"sku": "NEG", "quantity": -1}]}
      """
    Then the response status should be 400

  Scenario: Bulk edit rejects integration warehouse
    When I PATCH the v2 admin endpoint "qms/admin/warehouses/wh-integration/stock/edit/" with body
      """
      {"items": [{"sku": "X", "quantity": 1}]}
      """
    Then the response status should be 400

  # --- Integration Warehouse ---

  Scenario: Integration warehouse is read-only via source_type
    When I GET the v2 admin endpoint "qms/admin/warehouses/wh-integration/"
    Then the response status should be 200
    And the response field "source_type" should equal "integration"
    And the response field "last_synced_at" should not be null
