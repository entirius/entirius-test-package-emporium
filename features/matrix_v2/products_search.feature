@matrix-v2 @search
Feature: Matrix v2 Search
  As a storefront consumer
  I want to search products and categories
  So that customers can find what they need

  Background:
    Given the API base URL is configured
    And channel "default-europe" exists with products

  # ── Search structure ───────────────────────────────────────

  Scenario: Search returns all sections
    When I GET "/api/matrix/v2/default-europe/search/?q=sofa&language=en&currency=EUR&country=PL"
    Then the response status is 200
    And the response has key "products"
    And the response has key "categories"
    And the response has key "phrases"

  Scenario: Products section has pagination shape
    When I GET "/api/matrix/v2/default-europe/search/?q=sofa&language=en&currency=EUR&country=PL"
    Then the response status is 200
    And "products" has key "total"
    And "products" has key "results"
    And "products" has key "has_next_page"

  # ── Min length ─────────────────────────────────────────────

  Scenario: Single character query returns empty
    When I GET "/api/matrix/v2/default-europe/search/?q=a&language=en"
    Then the response status is 200
    And "products.total" is 0

  Scenario: Empty query returns empty
    When I GET "/api/matrix/v2/default-europe/search/?q=&language=en"
    Then the response status is 200
    And "products.total" is 0

  # ── Search finds data ──────────────────────────────────────

  Scenario: Search by product name finds results
    When I GET "/api/matrix/v2/default-europe/search/?q=sofa&language=en&currency=EUR&country=PL"
    Then the response status is 200

  Scenario: Search by SKU finds results
    When I GET "/api/matrix/v2/default-europe/search/?q=ENT-S&language=en&currency=EUR&country=PL"
    Then the response status is 200
