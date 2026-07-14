@admin @deliverypoints @v2 @crud @dp-points
Feature: Delivery Points Admin API -- Point CRUD
  As an admin user
  I want to create, read, update, and delete delivery points
  So that I can manage carrier and custom pickup locations

  # Note: carrier types (inpost=1, dpd=2, orlen=3, poczta_polska=4, dhl=5) are managed
  # exclusively by the import system. Tests use non-carrier types:
  #   showroom (PK=6, is_carrier=false)
  #   retail_store (PK=7, is_carrier=false)

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- Full CRUD Lifecycle ---

  Scenario: Point CRUD lifecycle (create, retrieve, update, delete)
    # Cleanup
    Given I ensure delivery point with code "BDD-POINT-001" is cleaned up
    # Create (using fixture type showroom PK=6, is_carrier=false)
    When I POST to the v2 admin endpoint "deliverypoints/admin/points/" with body
      """
      {
        "type_id": 6,
        "code": "BDD-POINT-001",
        "name": "BDD Test Point Warsaw",
        "latitude": "52.2297",
        "longitude": "21.0122",
        "street": "ul. Testowa 1",
        "city": "Warsaw",
        "state": "Masovian",
        "post_code": "00-001",
        "country": "PL",
        "phone": "+48 123 456 789",
        "email": "test@example.com",
        "is_active": true
      }
      """
    Then the response status should be 201
    And the response field "code" should equal "BDD-POINT-001"
    And the response field "name" should equal "BDD Test Point Warsaw"
    And the response field "city" should equal "Warsaw"
    And the response field "country" should equal "PL"
    And the response field "is_active" should be true
    And the response field "type" should be a dict
    And the response field "latitude" should not be null
    And the response field "longitude" should not be null
    Then I save the response field "id" as "saved.point_pk"
    # Retrieve
    When I GET the v2 admin endpoint "deliverypoints/admin/points/{saved.point_pk}/"
    Then the response status should be 200
    And the response should have the fields
      | field      |
      | id         |
      | type       |
      | code       |
      | name       |
      | latitude   |
      | longitude  |
      | street     |
      | city       |
      | state      |
      | post_code  |
      | country    |
      | phone      |
      | email      |
      | website    |
      | is_active  |
      | created_at |
      | modified_at |
    And the response field "code" should equal "BDD-POINT-001"
    And the response nested field "type.code" should equal "showroom"
    # Update
    When I PATCH the v2 admin endpoint "deliverypoints/admin/points/{saved.point_pk}/" with body
      """
      {"city": "Krakow", "post_code": "30-001", "is_active": false}
      """
    Then the response status should be 200
    And the response field "city" should equal "Krakow"
    And the response field "post_code" should equal "30-001"
    And the response field "is_active" should be false
    # Verify update persisted
    When I GET the v2 admin endpoint "deliverypoints/admin/points/{saved.point_pk}/"
    Then the response status should be 200
    And the response field "city" should equal "Krakow"
    And the response field "is_active" should be false
    # Delete
    When I DELETE the v2 admin endpoint "deliverypoints/admin/points/{saved.point_pk}/"
    Then the response status should be 204
    # Verify deleted
    When I GET the v2 admin endpoint "deliverypoints/admin/points/{saved.point_pk}/"
    Then the response status should be 404

  # --- Search & Filters ---

  Scenario: Points list supports search by city
    Given I ensure delivery point with code "BDD-SEARCH-001" is cleaned up
    When I POST to the v2 admin endpoint "deliverypoints/admin/points/" with body
      """
      {
        "type_id": 6,
        "code": "BDD-SEARCH-001",
        "name": "BDD Searchable Gdansk",
        "city": "Gdansk",
        "country": "PL"
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.search_pk"
    When I GET the v2 admin endpoint "deliverypoints/admin/points/" with params
      | param  | value  |
      | search | Gdansk |
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "code" equal to "BDD-SEARCH-001"
    # Cleanup
    When I DELETE the v2 admin endpoint "deliverypoints/admin/points/{saved.search_pk}/"
    Then the response status should be 204

  Scenario: Points list supports type filter
    Given I ensure delivery point with code "BDD-FILTER-001" is cleaned up
    When I POST to the v2 admin endpoint "deliverypoints/admin/points/" with body
      """
      {
        "type_id": 6,
        "code": "BDD-FILTER-001",
        "name": "BDD Showroom Filter",
        "city": "Poznan",
        "country": "PL"
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.filter_pk"
    When I GET the v2 admin endpoint "deliverypoints/admin/points/" with params
      | param | value    |
      | type  | showroom |
    Then the response status should be 200
    And the results should contain an item with "code" equal to "BDD-FILTER-001"
    # Cleanup
    When I DELETE the v2 admin endpoint "deliverypoints/admin/points/{saved.filter_pk}/"
    Then the response status should be 204

  Scenario: Points list supports is_active filter
    Given I ensure delivery point with code "BDD-ACTIVE-001" is cleaned up
    When I POST to the v2 admin endpoint "deliverypoints/admin/points/" with body
      """
      {
        "type_id": 7,
        "code": "BDD-ACTIVE-001",
        "name": "BDD Active Filter",
        "city": "Wroclaw",
        "country": "PL",
        "is_active": false
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.active_pk"
    When I GET the v2 admin endpoint "deliverypoints/admin/points/" with params
      | param     | value |
      | is_active | false |
    Then the response status should be 200
    And the results should contain an item with "code" equal to "BDD-ACTIVE-001"
    When I GET the v2 admin endpoint "deliverypoints/admin/points/" with params
      | param     | value |
      | is_active | true  |
    Then the response status should be 200
    And the results should not contain an item with "code" equal to "BDD-ACTIVE-001"
    # Cleanup
    When I DELETE the v2 admin endpoint "deliverypoints/admin/points/{saved.active_pk}/"
    Then the response status should be 204

  # --- Channel-Scoped List ---

  Scenario: Channel-scoped points list returns paginated structure
    When I GET the v2 admin endpoint "deliverypoints/admin/{channel_idx}/points/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  # --- Error Cases ---

  Scenario: Create point with invalid type_id returns 400
    When I POST to the v2 admin endpoint "deliverypoints/admin/points/" with body
      """
      {
        "type_id": 99999,
        "code": "BDD-BAD-TYPE",
        "name": "Invalid Type Point"
      }
      """
    Then the response status should be 400

  Scenario: Retrieve non-existent point returns 404
    When I GET the v2 admin endpoint "deliverypoints/admin/points/99999/"
    Then the response status should be 404

  Scenario: Delete non-existent point returns 404
    When I DELETE the v2 admin endpoint "deliverypoints/admin/points/99999/"
    Then the response status should be 404
