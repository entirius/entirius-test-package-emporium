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
    And "products.results" has at least 1 item
    And "products.total" is at least 1

  Scenario: Search by SKU finds results
    When I GET "/api/matrix/v2/default-europe/search/?q=ENT-S&language=en&currency=EUR&country=PL"
    Then the response status is 200
    And "products.results" has at least 1 item

  Scenario: Search with no match returns empty
    When I GET "/api/matrix/v2/default-europe/search/?q=xyznonexistent12345zzz&language=en&currency=EUR&country=PL"
    Then the response status is 200
    And "products.total" is 0
    And "products.results" has exactly 0 items

  # ── total is the match count, not the page size ────────────

  Scenario: Total exceeds the page size when more matches exist
    When I GET "/api/matrix/v2/default-europe/search/?q=sofa&page_size=2&scope=products&language=en&currency=EUR&country=PL"
    Then the response status is 200
    And "products.results" has exactly 2 items
    And "products.has_next_page" is true
    And "products.total" is greater than the number of items in "products.results"

  Scenario: Total stays the same on the last page
    When I GET "/api/matrix/v2/default-europe/search/?q=sofa&page=3&page_size=2&scope=products&language=en&currency=EUR&country=PL"
    Then the response status is 200
    And "products.total" is at least 3

  # ── Unknown params warn, never reject ──────────────────────

  Scenario: Unknown query param is reported in meta, not rejected
    When I GET "/api/matrix/v2/default-europe/search/?q=sofa&utm_source=newsletter&language=en&currency=EUR&country=PL"
    Then the response status is 200
    And "meta.status" is "warning"
    And "meta.warnings" has exactly 1 item

  Scenario: Declared params produce no warnings
    When I GET "/api/matrix/v2/default-europe/search/?q=sofa&limit=3&page=1&page_size=12&scope=products&language=en&currency=EUR&country=PL"
    Then the response status is 200
    And "meta.status" is "ok"
