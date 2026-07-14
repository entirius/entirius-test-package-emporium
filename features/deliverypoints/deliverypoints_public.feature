@deliverypoints @v2 @public
Feature: Delivery Points Public API v2
  As a storefront user
  I want to view delivery points and types
  So that I can select a pickup location for my order

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  # --- Public Types ---

  Scenario: Public types list accessible without auth
    When I GET the v2 admin endpoint "deliverypoints/{channel_idx}/types/" without auth
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Public types list contains active fixture types
    When I GET the v2 admin endpoint "deliverypoints/{channel_idx}/types/" without auth
    Then the response status should be 200
    And the results count should be greater than 0
    And the results should contain an item with "code" equal to "inpost"
    And the results should contain an item with "code" equal to "dpd"

  # --- Public Points ---

  Scenario: Public points list accessible without auth
    When I GET the v2 admin endpoint "deliverypoints/{channel_idx}/points/" without auth
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  # --- Nearby Endpoint ---

  Scenario: Nearby endpoint requires lat and lng params
    When I GET the v2 admin endpoint "deliverypoints/{channel_idx}/points/nearby/" without auth
    Then the response status should be 400

  Scenario: Nearby endpoint with valid coordinates returns 200
    When I GET the v2 admin endpoint "deliverypoints/{channel_idx}/points/nearby/?lat=52.2297&lng=21.0122" without auth
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | results  |
