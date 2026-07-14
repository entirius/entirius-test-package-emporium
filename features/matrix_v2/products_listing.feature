@matrix-v2 @products
Feature: Matrix v2 Products Listing
  As a storefront consumer
  I want to fetch product listings from the v2 API
  So that I get complete product data with gross/net prices in one call

  Background:
    Given the API base URL is configured
    And channel "default-europe" exists with products

  Scenario: Listing returns paginated shape
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL"
    Then the response status is 200
    And the response has key "has_next_page"
    And the response has key "page"
    And the response has key "page_size"
    And the response has key "results"
    And "results" is a list

  Scenario: Core product fields present
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&page_size=1"
    Then the response status is 200
    And the first result has key "sku"
    And the first result has key "product_type"
    And the first result has key "is_virtual"
    And the first result has key "url_key"
    And the first result has key "name"
    And the first result has key "price"
    And the first result has key "categories"

  Scenario: Price object has gross and net
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sku=ENT-S004"
    Then the response status is 200
    And the first result price has key "gross"
    And the first result price has key "net"
    And the first result price has key "final_gross"
    And the first result price has key "final_net"
    And the first result price has key "tax_rate"
    And the first result price has key "currency"

  Scenario: No include returns core only
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&page_size=1"
    Then the response status is 200
    And the first result does not have key "attributes"
    And the first result does not have key "visual_assets"
    And the first result does not have key "description"
    And the first result does not have key "media"
    And the first result does not have key "variants"

  Scenario: Include full adds all groups
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&page_size=1&include=full"
    Then the response status is 200
    And the first result has key "attributes"
    And the first result has key "visual_assets"
    And the first result has key "url_keys"
    And the first result has key "meta_title"
    And the first result has key "description"
    And the first result has key "media"
    And the first result has key "variants"
    And the first result has key "children_skus"

  Scenario: SKU batch lookup returns single product
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&sku=ENT-S004"
    Then the response status is 200
    And "results" has exactly 1 item
    And "has_next_page" is false

  Scenario: Page size capped at 100
    When I GET "/api/matrix/v2/default-europe/products/?language=en&currency=EUR&country=PL&page_size=999"
    Then the response status is 200
    And "page_size" is at most 100

  Scenario: v1 listing still works
    When I GET "/api/matrix/v1/default-europe/products/?language=en&currency=EUR&country=PL&limit=1"
    Then the response status is 200
    And the response has key "data"
    And the response has key "pagination"
