@admin @faq @faq-items @v2 @crud
Feature: FAQ Admin API -- Item CRUD
  As an admin user
  I want to create, read, update, and delete FAQ items
  So that I can manage Q&A pairs with optional entity associations

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  # --- List ---

  Scenario: Items list returns paginated structure
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/items/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Items list contains fixture items
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/items/"
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "url_key" equal to "how-long-does-shipping-take"

  # --- Full CRUD Lifecycle with Associations ---

  Scenario: Item CRUD lifecycle with entity association (create, retrieve, update, delete)
    # Cleanup from previous runs
    Given I ensure faq item with url_key "bdd-test-item-001" is cleaned up
    # Create with association
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/items/" with body
      """
      {
        "url_key": "bdd-test-item-001",
        "question": "BDD Test Question?",
        "answer": "<p>BDD Test Answer.</p>",
        "short_answer": "BDD Short",
        "group_idx": "shipping",
        "position": 99,
        "is_active": true,
        "associations": [
          {"entity_type": "product", "entity_identifier": "BDD-PROD-001"}
        ]
      }
      """
    Then the response status should be 201
    And the response field "url_key" should equal "bdd-test-item-001"
    And the response field "question" should equal "BDD Test Question?"
    And the response field "is_active" should be true
    And the response field "group_idx" should equal "shipping"
    And the response field "associations" should be a list
    And the response field "translations" should be a list
    Then I save the response field "id" as "saved.item_pk"
    # Retrieve
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.item_pk}/"
    Then the response status should be 200
    And the response should have the fields
      | field            |
      | id               |
      | url_key          |
      | question         |
      | answer           |
      | short_answer     |
      | image_url        |
      | group_idx        |
      | group_name       |
      | position         |
      | position_in_group|
      | is_active        |
      | translations     |
      | associations     |
    And the response field "url_key" should equal "bdd-test-item-001"
    And the response field "group_idx" should equal "shipping"
    # Update
    When I PATCH the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.item_pk}/" with body
      """
      {
        "question": "BDD Updated Question?",
        "is_active": false
      }
      """
    Then the response status should be 200
    And the response field "question" should equal "BDD Updated Question?"
    And the response field "is_active" should be false
    # Verify update persisted
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.item_pk}/"
    Then the response status should be 200
    And the response field "question" should equal "BDD Updated Question?"
    And the response field "is_active" should be false
    # Delete
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.item_pk}/"
    Then the response status should be 204
    # Verify deleted
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.item_pk}/"
    Then the response status should be 404

  # --- Item Filters ---

  Scenario: Items list supports filter by group
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/items/" with params
      | param | value    |
      | group | shipping |
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "url_key" equal to "how-long-does-shipping-take"

  Scenario: Items list supports search by question text
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/items/" with params
      | param  | value    |
      | search | shipping |
    Then the response status should be 200
    And the results count should be greater than 0

  # --- Item Translations ---

  Scenario: Create, update, and delete an item translation
    Given I ensure faq item with url_key "bdd-t9n-item-001" is cleaned up
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/items/" with body
      """
      {
        "url_key": "bdd-t9n-item-001",
        "question": "BDD Translation Item?",
        "answer": "<p>BDD Answer.</p>",
        "is_active": true
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.t9n_item_pk"
    # Create translation
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.t9n_item_pk}/translations/" with body
      """
      {
        "language": "pl",
        "question": "BDD Pytanie testowe?",
        "answer": "<p>BDD Odpowiedź testowa.</p>",
        "short_answer": "Krótka odpowiedź"
      }
      """
    Then the response status should be 201
    And the response field "language" should equal "pl"
    And the response field "question" should equal "BDD Pytanie testowe?"
    And the response field "answer" should not be null
    And the response field "short_answer" should equal "Krótka odpowiedź"
    # Update translation
    When I PATCH the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.t9n_item_pk}/translations/pl/" with body
      """
      {"question": "BDD Pytanie zmienione?"}
      """
    Then the response status should be 200
    And the response field "question" should equal "BDD Pytanie zmienione?"
    # Verify in translations list
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.t9n_item_pk}/translations/"
    Then the response status should be 200
    # Delete translation
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.t9n_item_pk}/translations/pl/"
    Then the response status should be 204
    # Cleanup item
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.t9n_item_pk}/"
    Then the response status should be 204

  # --- Error Cases ---

  Scenario: Create item with duplicate url_key returns 400
    Given I ensure faq item with url_key "bdd-dup-url-key" is cleaned up
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/items/" with body
      """
      {"url_key": "bdd-dup-url-key", "question": "First Question?", "answer": "<p>First.</p>"}
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.dup_pk"
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/items/" with body
      """
      {"url_key": "bdd-dup-url-key", "question": "Duplicate?", "answer": "<p>Dup.</p>"}
      """
    Then the response status should be 400
    # Cleanup
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.dup_pk}/"
    Then the response status should be 204

  Scenario: Retrieve non-existent item returns 404
    When I GET the v2 admin endpoint "faq/admin/{channel_idx}/items/99999/"
    Then the response status should be 404

  Scenario: Delete non-existent item returns 404
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/items/99999/"
    Then the response status should be 404

  Scenario: Update non-existent item returns 404
    When I PATCH the v2 admin endpoint "faq/admin/{channel_idx}/items/99999/" with body
      """
      {"question": "Does not matter"}
      """
    Then the response status should be 404
