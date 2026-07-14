@matrix-v2 @products @filters
Feature: Matrix v2 Product Filters & Sorting
  As a storefront consumer
  I want to filter and sort products via query params
  So that the listing page shows relevant results in the right order

  Background:
    Given the API base URL is configured
    And channel "default-europe" exists with products

  # ── Stock filter ───────────────────────────────────────────

  Scenario: Filter by on_stock returns 200
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&on_stock=true"
    Then the response status is 200
    And "results" is a list

  # ── Product type filter ────────────────────────────────────

  Scenario: Filter by product_type SIMPLE
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&product_type=SIMPLE&page_size=3"
    Then the response status is 200

  # ── SKU batch lookup ───────────────────────────────────────

  Scenario: Batch SKU lookup returns requested products
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sku=ENT-S004"
    Then the response status is 200

  # ── Sorting ────────────────────────────────────────────────

  Scenario: Sort by name ascending
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sort=name&sort_dir=asc&page_size=5"
    Then the response status is 200
    And "results" is a list

  Scenario: Sort by price ascending
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sort=price&sort_dir=asc&page_size=5"
    Then the response status is 200

  # ── Category filter ────────────────────────────────────────

  Scenario: Filter by category returns products
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&category=sofas&page_size=5"
    Then the response status is 200

  # ── Range filter (r_*) — both query-param formats ─────────

  @range
  Scenario: Range filter in repeated-param form is applied (regression)
    # Canonical URLSearchParams form: r_price=A&r_price=B.
    # Before the fix the backend read only the first value and silently
    # dropped the filter, returning the full unfiltered list. An impossible
    # range must now produce zero results.
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&r_price=99999998&r_price=99999999&page_size=100"
    Then the response status is 200
    And "results" is a list
    And "results" has exactly 0 items

  @range
  Scenario: Range filter in comma-separated form remains supported
    # Legacy form used by the Nuxt storefront-blueprint: r_price=A,B.
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&r_price=99999998,99999999&page_size=100"
    Then the response status is 200
    And "results" is a list
    And "results" has exactly 0 items

  # ── Unknown channel ────────────────────────────────────────

  Scenario: Unknown channel returns 404
    When I GET "/api/matrix/v2/nonexistent-channel/products/?language=en&currency=EUR&country=PL"
    Then the response status is 404
