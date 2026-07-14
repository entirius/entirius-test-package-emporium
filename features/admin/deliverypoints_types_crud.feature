@admin @deliverypoints @v2 @crud @dp-types
Feature: Delivery Points Admin API -- Type CRUD
  As an admin user
  I want to create, read, update, and delete delivery point types
  So that I can manage available carrier and custom location categories

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- Fixture Types ---

  Scenario: Retrieve fixture type by PK returns expected fields
    When I GET the v2 admin endpoint "deliverypoints/admin/types/1/"
    Then the response status should be 200
    And the response should have the fields
      | field      |
      | id         |
      | code       |
      | name       |
      | is_carrier |
      | is_active  |
      | sort_order |
      | created_at |
      | modified_at |
    And the response field "code" should equal "inpost"
    And the response field "name" should equal "InPost"
    And the response field "is_carrier" should be true
    And the response field "is_active" should be true

  # --- Full CRUD Lifecycle ---

  Scenario: Type CRUD lifecycle (create, retrieve, update, delete)
    # Cleanup
    Given I ensure delivery type with code "bdd-test-type" is cleaned up
    # Create (is_carrier=false so it can be updated and deleted)
    When I POST to the v2 admin endpoint "deliverypoints/admin/types/" with body
      """
      {
        "code": "bdd-test-type",
        "name": "BDD Test Type",
        "is_carrier": false,
        "is_active": true,
        "sort_order": 99
      }
      """
    Then the response status should be 201
    And the response field "code" should equal "bdd-test-type"
    And the response field "name" should equal "BDD Test Type"
    And the response field "is_carrier" should be false
    And the response field "is_active" should be true
    And the response field "sort_order" should equal integer 99
    Then I save the response field "id" as "saved.type_pk"
    # Retrieve
    When I GET the v2 admin endpoint "deliverypoints/admin/types/{saved.type_pk}/"
    Then the response status should be 200
    And the response field "code" should equal "bdd-test-type"
    And the response field "name" should equal "BDD Test Type"
    # Update
    When I PATCH the v2 admin endpoint "deliverypoints/admin/types/{saved.type_pk}/" with body
      """
      {"name": "BDD Updated Type", "is_active": false}
      """
    Then the response status should be 200
    And the response field "name" should equal "BDD Updated Type"
    And the response field "is_active" should be false
    # Verify update persisted
    When I GET the v2 admin endpoint "deliverypoints/admin/types/{saved.type_pk}/"
    Then the response status should be 200
    And the response field "name" should equal "BDD Updated Type"
    And the response field "is_active" should be false
    # Delete
    When I DELETE the v2 admin endpoint "deliverypoints/admin/types/{saved.type_pk}/"
    Then the response status should be 204
    # Verify deleted
    When I GET the v2 admin endpoint "deliverypoints/admin/types/{saved.type_pk}/"
    Then the response status should be 404

  # --- Error Cases ---

  Scenario: Create type with duplicate code returns 400
    Given I ensure delivery type with code "bdd-dup-code" is cleaned up
    When I POST to the v2 admin endpoint "deliverypoints/admin/types/" with body
      """
      {"code": "bdd-dup-code", "name": "First Type", "is_carrier": false}
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.dup_pk"
    When I POST to the v2 admin endpoint "deliverypoints/admin/types/" with body
      """
      {"code": "bdd-dup-code", "name": "Duplicate", "is_carrier": false}
      """
    Then the response status should be 400
    # Cleanup
    When I DELETE the v2 admin endpoint "deliverypoints/admin/types/{saved.dup_pk}/"
    Then the response status should be 204

  Scenario: Retrieve non-existent type returns 404
    When I GET the v2 admin endpoint "deliverypoints/admin/types/99999/"
    Then the response status should be 404

  Scenario: Delete non-existent type returns 404
    When I DELETE the v2 admin endpoint "deliverypoints/admin/types/99999/"
    Then the response status should be 404
