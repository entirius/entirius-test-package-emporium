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

  # ── Sorting (s_<field>=<dir> prefix, consistent with q_ / r_) ──

  Scenario: Sort by name ascending
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&s_name=asc&page_size=5"
    Then the response status is 200
    And "results" is a list

  Scenario: Sort by price ascending
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&s_price=asc&page_size=5"
    Then the response status is 200

  Scenario: Multi-sort by repeated s_ params (URL order = precedence)
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&s_price=asc&s_name=asc&page_size=5"
    Then the response status is 200
    And "results" is a list

  Scenario: Sort by a sortable feature idx
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&s_weight_kg=asc&page_size=5"
    Then the response status is 200
    And "results" is a list

  # Status 200 alone cannot tell the two sort contracts apart -- an ignored param
  # is still a 200. meta is what separates "recognised" from "silently dropped".

  Scenario: A s_ sort param is recognised, not dropped
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&s_name=asc&page_size=5"
    Then the response status is 200
    And "meta.status" is "ok"
    And "meta.warnings" has exactly 0 items

  Scenario: The retired sort/sort_dir pair is reported as unknown
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sort=name&sort_dir=asc&page_size=5"
    Then the response status is 200
    And "meta.status" is "warning"
    And "meta.warnings" has exactly 2 items

  # The warning code carries the whole point: a param the API never heard of also
  # yields status=warning with one entry, so only the code separates "s_ prefix
  # understood, field not sortable" from "s_ prefix not supported at all".
  Scenario: A s_ param naming an unsortable field is reported
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&s_bogus_field=asc&page_size=5"
    Then the response status is 200
    And "meta.status" is "warning"
    And "meta.warnings" has exactly 1 item
    And "meta.warnings.0.code" is "sort.unknown_field"

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

  # ── Free-text search on the listing ────────────────────────
  # v1 honours ?search= on products/; v2 must not silently drop the param and
  # return the full catalogue. Mirrors features/matrix/search.feature.

  @search
  Scenario: Search narrows the listing
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&search=Sofa&page_size=100"
    Then the response status is 200
    And "results" has at least 1 item

  @search
  Scenario: Search with no match returns empty
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&search=xyznonexistent12345zzz&page_size=100"
    Then the response status is 200
    And "results" has exactly 0 items

  @search
  Scenario: Blank search is not a filter
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&search=&page_size=100"
    Then the response status is 200
    And "results" has at least 1 item

  @search
  Scenario: Count endpoint honours search
    When I GET "/api/matrix/v2/default-europe/products/count/?language=en&currency=EUR&country=PL&search=xyznonexistent12345zzz"
    Then the response status is 200
    And "count" is 0

  # ── Unknown query params ───────────────────────────────────

  Scenario: Tracking param is reported in meta, not rejected
    # Storefront forwards the whole browser query string, so 400 would break the page.
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&utm_source=newsletter&page_size=1"
    Then the response status is 200
    And "meta.status" is "warning"
    And "meta.warnings" has exactly 1 item

  Scenario: Legacy v1 limit param is reported, not honoured
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&limit=1&page_size=5"
    Then the response status is 200
    And "results" has exactly 5 items
    And "meta.status" is "warning"

  Scenario: Declared params produce no warnings
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&page=1&page_size=5&include=visual_assets&search=Sofa&product_type=SIMPLE&on_stock=true"
    Then the response status is 200
    And "meta.status" is "ok"

  # ── Unknown channel ────────────────────────────────────────

  Scenario: Unknown channel returns 404
    When I GET "/api/matrix/v2/nonexistent-channel/products/?language=en&currency=EUR&country=PL"
    Then the response status is 404
