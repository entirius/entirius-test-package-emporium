@contentdb @import-verification
Feature: ContentDB Published Content API
  As an API consumer
  I want to retrieve published content pages
  So that the storefront can render CMS pages

  Background:
    Given the test package has been imported

  Scenario: Homepage exists at route home
    When I GET the ContentDB published endpoint "static-page/" with routes "home"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Homepage content has sections and tiles
    When I GET the ContentDB published endpoint "static-page/" with routes "home"
    Then the response status should be 200
    And the first item content should have sections_order
    And the first item content should have tiles

  Scenario: Published content has required fields
    When I GET the ContentDB published endpoint "static-page/" with routes "home"
    Then the response status should be 200
    And each item should have the fields
      | field   |
      | uid     |
      | content |
      | meta    |

  Scenario: About page exists
    When I GET the ContentDB published endpoint "static-page/" with routes "about"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Contact page exists
    When I GET the ContentDB published endpoint "static-page/" with routes "contact"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Homepage hero tile has images_set
    When I GET the ContentDB published endpoint "static-page/" with routes "home"
    Then the response status should be 200
    And the first hero tile should have images_set with desktop

  Scenario: Homepage has expected tile types
    When I GET the ContentDB published endpoint "static-page/" with routes "home"
    Then the response status should be 200
    And the tiles should include core_type "tile-hero"

  Scenario: Homepage tiles have dye set
    When I GET the ContentDB published endpoint "static-page/" with routes "home"
    Then the response status should be 200
    And the first hero tile should have a dye value

  Scenario: Product Showcase page exists at route product-showcase
    When I GET the ContentDB published endpoint "static-page/" with routes "product-showcase"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Product Showcase has hero tiles with product_sku
    When I GET the ContentDB published endpoint "static-page/" with routes "product-showcase"
    Then the response status should be 200
    And the tiles should include core_type "tile-hero"
    And the tiles should include a tile with product_sku "ENT-S001"
    And the tiles should include a tile with product_sku "ENT-S003"
    And the tiles should include a tile with product_sku "ENT-C001"

  Scenario: Non-existent page returns bad request
    When I GET the ContentDB published endpoint "static-page/" with routes "nonexistent-page-xyz"
    Then the response status should be 400
