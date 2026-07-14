@matrix-v2 @stock @prices @omnibus
Feature: Matrix v2 Simple Endpoints
  Stock, options, categories, search, omnibus

  Background:
    Given the API base URL is configured
    And channel "default-europe" exists with products

  # ── Stock ────────────────────────────────────────────

  Scenario: Stock returns keyed response
    When I GET "/api/matrix/v2/default-europe/stock/?sku=ENT-S004"
    Then the response status is 200
    And the response is a dict

  Scenario: Stock has no-store cache header
    When I GET "/api/matrix/v2/default-europe/stock/?sku=ENT-S004"
    Then the response header "Cache-Control" is "no-store"

  Scenario: Stock empty without SKUs
    When I GET "/api/matrix/v2/default-europe/stock/"
    Then the response status is 200
    And the response is empty dict

  # ── Options ──────────────────────────────────────────

  Scenario: Options returns pre-grouped sections
    When I GET "/api/matrix/v2/default-europe/options/?language=en&currency=EUR&country=PL"
    Then the response status is 200
    And the response has key "sort"
    And the response has key "ranges"
    And the response has key "filters"
    And "sort" is a list
    And "ranges" is a list
    And "filters" is a list

  # ── Categories ───────────────────────────────────────

  Scenario: Categories returns nested tree
    When I GET "/api/matrix/v2/default-europe/categories/?language=en"
    Then the response status is 200
    And the response is a list

  Scenario: Single category wraps in results
    When I GET "/api/matrix/v2/default-europe/categories/?language=en&url_key=nonexistent"
    Then the response status is 200
    And the response has key "results"

  # ── Search ───────────────────────────────────────────

  Scenario: Search returns sections
    When I GET "/api/matrix/v2/default-europe/search/?q=chair&language=en&currency=EUR&country=PL"
    Then the response status is 200
    And the response has key "products"
    And the response has key "categories"
    And the response has key "phrases"

  Scenario: Search short query returns empty
    When I GET "/api/matrix/v2/default-europe/search/?q=a&language=en"
    Then the response status is 200
    And "products" has key "total"
    And "products.total" is 0

  # ── Omnibus ──────────────────────────────────────────

  Scenario: Omnibus returns keyed response
    When I GET "/api/matrix/v2/default-europe/omnibus/?sku=ENT-S004&currency=EUR&country=PL"
    Then the response status is 200
    And the response is a dict

  Scenario: Omnibus returns populated omnibus_gross for promo SKU
    When I GET "/api/matrix/v2/default-europe/omnibus/?sku=ENT-C004&currency=EUR&country=PL"
    Then the response status is 200
    And the response nested field "ENT-C004.omnibus_gross" should not be null

  # ── Count ────────────────────────────────────────────

  Scenario: Count returns integer
    When I GET "/api/matrix/v2/default-europe/products/count/?language=en&currency=EUR&country=PL"
    Then the response status is 200
    And the response has key "count"
