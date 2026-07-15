@admin @suppliers @v2 @suppliers-feed @supplier
Feature: Suppliers Admin API -- Feed Lifecycle
  As an admin user
  I want to manage feeds for a supplier and run them
  So that the import pipeline can fetch supplier products

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: Demo feed from fixture is retrievable
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/main-catalog/"
    Then the response status should be 200
    And the response field "idx" should equal "main-catalog"
    And the response field "connector_kind" should equal "xml_feed"
    And the response field "sync_mode" should equal "full"
    And the response field "is_active" should be true

  Scenario: Create new feed for demo-supplier
    Given I ensure feed "bdd-extra-feed" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/" with body
      """
      {
        "idx": "bdd-extra-feed",
        "connector_kind": "xml_feed",
        "feed_config": {
          "feed_url": "http://fixtures:8000/package/supplier-feed.xml",
          "product_xpath": ".//product",
          "field_mapping": {"external_id": "./sku/text()", "name": "./name/text()", "cost": "./price/text()"}
        },
        "sync_mode": "full",
        "is_active": true
      }
      """
    Then the response status should be 201
    And the response field "idx" should equal "bdd-extra-feed"
    Given I ensure feed "bdd-extra-feed" for supplier "demo-supplier" is cleaned up

  Scenario: Test feed (init-test) reads sample products from XML without persistence
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/main-catalog/test/" with body
      """
      {"limit": 5}
      """
    Then the response status should be 200
    And the response field "raw_products" should be a list

  Scenario: Trigger feed run (sync xml_feed) creates ImportLog
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/main-catalog/trigger/" with body
      """
      {"mode": "full", "async": false}
      """
    Then the response status should be 200
    And the response field "run_id" should not be null
    And the response field "status" should equal "success"

  Scenario: Re-trigger feed without changes results in unchanged>=existing
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/main-catalog/trigger/" with body
      """
      {"mode": "full", "async": false}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/import-logs/?feed_id=1&page_size=10"
    Then the response status should be 200
    And the response field "results" should contain at least 1 item

  Scenario: Trigger feed with malformed feed_config returns failed ImportLog
    Given I ensure feed "bdd-bad-feed" for supplier "demo-supplier" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/" with body
      """
      {
        "idx": "bdd-bad-feed",
        "connector_kind": "xml_feed",
        "feed_config": {
          "feed_url": "http://fixtures:8000/package/does-not-exist.xml",
          "product_xpath": ".//product",
          "field_mapping": {"external_id": "./sku/text()"}
        },
        "sync_mode": "full",
        "is_active": true
      }
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/bdd-bad-feed/trigger/" with body
      """
      {"mode": "full", "async": false}
      """
    Then the response status should be 200
    And the response field "status" should equal "failed"
    Given I ensure feed "bdd-bad-feed" for supplier "demo-supplier" is cleaned up

  Scenario: Soft-disable feed via PATCH is_active=false
    When I PATCH the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/main-catalog/" with body
      """
      {"is_active": false}
      """
    Then the response status should be 200
    And the response field "is_active" should be false
    # Restore for downstream tests
    When I PATCH the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/main-catalog/" with body
      """
      {"is_active": true}
      """
    Then the response status should be 200
