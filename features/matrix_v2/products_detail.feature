@matrix-v2 @products @detail
Feature: Matrix v2 Product Detail & Data Validation
  As a storefront consumer
  I want product detail responses to contain correct, complete data
  So that the PDP renders correctly with accurate prices and attributes

  Background:
    Given the API base URL is configured
    And channel "default-europe" exists with products

  # ── Core response shape ────────────────────────────────────

  Scenario: Listing returns results list
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&page_size=3"
    Then the response status is 200
    And "results" is a list

  Scenario: Product has core fields
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sku=ENT-S004"
    Then the response status is 200
    And the first result has key "sku"
    And the first result has key "product_type"
    And the first result has key "name"
    And the first result has key "url_key"
    And the first result has key "categories"

  Scenario: Categories are a list
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sku=ENT-S004"
    Then the response status is 200
    And the first result field "categories" is a list

  # ── Price data validation ──────────────────────────────────

  Scenario: Price has gross and net fields
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sku=ENT-S004"
    Then the response status is 200
    And the first result has key "price"
    And the first result price has key "gross"
    And the first result price has key "net"
    And the first result price has key "currency"
    And the first result price has key "tax_rate"
    And the first result price has key "is_range"

  Scenario: Price currency matches request
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sku=ENT-S004"
    Then the response status is 200
    And the first result price field "currency" equals "EUR"

  # ── Include=full detail ────────────────────────────────────

  Scenario: Full include has SEO fields
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sku=ENT-S004&include=full"
    Then the response status is 200
    And the first result has key "url_keys"
    And the first result has key "meta_title"
    And the first result has key "description"
    And the first result field "media" is a list
    And the first result field "children_skus" is a list

  # ── Include=attributes ─────────────────────────────────────

  Scenario: Attributes include returns attribute list
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sku=ENT-S004&include=attributes"
    Then the response status is 200
    And the first result has key "attributes"
