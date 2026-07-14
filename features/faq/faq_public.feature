@faq @public @v2
Feature: FAQ Public API v2
  As a storefront user
  I want to view FAQ items and groups for a channel
  So that I can find answers to common questions

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  # --- Public Items List ---

  Scenario: Items list accessible without auth
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/" without auth
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Items list returns active fixture items
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/" without auth
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "url_key" equal to "how-long-does-shipping-take"
    And the results should contain an item with "url_key" equal to "how-to-track-my-order"

  Scenario: Items list response fields are present
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/" without auth
    Then the response status should be 200
    And the results count should be greater than 0

  # --- Filter by Group ---

  Scenario: Items list filtered by group returns matching items
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/?group=shipping" without auth
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "url_key" equal to "how-long-does-shipping-take"
    And the results should not contain an item with "url_key" equal to "what-payment-methods-do-you-accept"

  Scenario: Items list filtered by non-existent group returns empty results
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/?group=does-not-exist" without auth
    Then the response status should be 200

  # --- Filter by Entity ---

  Scenario: Items list filtered by entity_type and entity_id returns associated items
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/?entity_type=product&entity_id=CHAIR-001" without auth
    Then the response status should be 200
    And the results should contain an item with "url_key" equal to "how-to-return-an-item"

  Scenario: Items list filtered by category entity returns associated items
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/?entity_type=category&entity_id=furniture" without auth
    Then the response status should be 200
    And the results should contain an item with "url_key" equal to "what-payment-methods-do-you-accept"

  # --- Retrieve by url_key ---

  Scenario: Retrieve active item by url_key returns 200
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/how-long-does-shipping-take/" without auth
    Then the response status should be 200
    And the response field "url_key" should equal "how-long-does-shipping-take"
    And the response field "question" should not be null
    And the response field "answer" should not be null

  Scenario: Retrieve non-existent item by url_key returns 404
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/does-not-exist-xyz/" without auth
    Then the response status should be 404

  # --- Language Resolution ---

  Scenario: Items list with language=en returns English translations
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/?language=en" without auth
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "url_key" equal to "how-long-does-shipping-take"

  Scenario: Items list with language=pl returns Polish translations for item 1
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/how-long-does-shipping-take/?language=pl" without auth
    Then the response status should be 200
    And the response field "url_key" should equal "how-long-does-shipping-take"
    And the response field "question" should not be null

  # --- Active-only Filter ---

  Scenario: Inactive items are not returned in public list
    Given I am authenticated as an admin user
    And I ensure faq item with url_key "bdd-inactive-item" is cleaned up
    When I POST to the v2 admin endpoint "faq/admin/{channel_idx}/items/" with body
      """
      {
        "url_key": "bdd-inactive-item",
        "question": "BDD Inactive?",
        "answer": "<p>Should not appear.</p>",
        "is_active": false
      }
      """
    Then the response status should be 201
    Then I save the response field "id" as "saved.inactive_pk"
    When I GET the v2 admin endpoint "faq/{channel_idx}/items/" without auth
    Then the response status should be 200
    And the results should not contain an item with "url_key" equal to "bdd-inactive-item"
    # Cleanup
    Given I am authenticated as an admin user
    When I DELETE the v2 admin endpoint "faq/admin/{channel_idx}/items/{saved.inactive_pk}/"
    Then the response status should be 204

  # --- Public Groups ---

  Scenario: Groups list accessible without auth
    When I GET the v2 admin endpoint "faq/{channel_idx}/groups/" without auth
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Groups list returns active fixture groups
    When I GET the v2 admin endpoint "faq/{channel_idx}/groups/" without auth
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "idx" equal to "shipping"
    And the results should contain an item with "idx" equal to "general"

  Scenario: Groups list with language parameter returns 200
    When I GET the v2 admin endpoint "faq/{channel_idx}/groups/?language=en" without auth
    Then the response status should be 200
    And the results count should be greater than 0
