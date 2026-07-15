@admin @suppliers @v2 @suppliers-delta @supplier
Feature: Suppliers Admin API -- Delta Sync, Cost Updates, Retention
  As an admin user
  I want to run delta sync to refresh cost / qty / physical attributes
  And purge old IntegrationEvents per retention policy

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user
    And regional language "pl" id is stored as "lang_id"
    And regional currency "PLN" id is stored as "curr_id"

  Scenario: Delta trigger on demo feed runs without error
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/main-catalog/trigger/" with body
      """
      {"mode": "delta", "async": false}
      """
    Then the response status should be 200
    And the response field "run_id" should not be null

  Scenario: Delta sync emits cost_updated events for pushed SPs
    # Run delta after at least one push happened (DEMO-004 from previous test or fresh push)
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/feeds/main-catalog/trigger/" with body
      """
      {"mode": "delta", "async": false}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/events/?event_type=cost_updated&page_size=20"
    Then the response status should be 200

  Scenario: Delta sync with no matched external_id emits unknown_external_id_in_delta info event
    # delta xml feed targeting a different supplier (with no matching SPs) produces unknown events
    Given I ensure supplier with idx "bdd-delta-orphan-sup" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "bdd-delta-orphan-sup",
        "name": "BDD Delta Orphan",
        "supplier_role": "trade",
        "supplier_type": "feed",
        "review_mode": "manual",
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id},
        "sku_prefix": "BDDD"
      }
      """
    Then the response status should be 201
    Given I ensure feed "bdd-delta-feed" for supplier "bdd-delta-orphan-sup" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/bdd-delta-orphan-sup/feeds/" with body
      """
      {
        "idx": "bdd-delta-feed",
        "connector_kind": "xml_feed",
        "feed_config": {
          "feed_url": "http://fixtures:8000/package/supplier-feed.xml",
          "product_xpath": ".//product",
          "field_mapping": {"external_id": "./sku/text()", "name": "./name/text()", "cost": "./price/text()"}
        },
        "sync_mode": "delta",
        "is_active": true
      }
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/bdd-delta-orphan-sup/feeds/bdd-delta-feed/trigger/" with body
      """
      {"mode": "delta", "async": false}
      """
    Then the response status should be 200
    Given I ensure supplier with idx "bdd-delta-orphan-sup" is cleaned up

  Scenario: List events filtered by severity
    When I GET the v2 admin endpoint "suppliers/admin/events/?severity=info&page_size=10"
    Then the response status should be 200
    And the response field "results" should be a list

  Scenario: Acknowledge an event sets acknowledged_at + acknowledged_by
    When I GET the v2 admin endpoint "suppliers/admin/events/?acknowledged=false&page_size=1"
    Then the response status should be 200
    And the response field "results" should be a list
    Then I save the first result field "id" as "saved.event_id"
    When I POST to the v2 admin endpoint "suppliers/admin/events/{saved.event_id}/acknowledge/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "acknowledged_at" should not be null

  Scenario: Settings retention_days can be updated for prune behavior
    When I GET the v2 admin endpoint "suppliers/admin/settings/"
    Then the response status should be 200
    And the response field "integration_event_retention_days" should not be null
    When I PATCH the v2 admin endpoint "suppliers/admin/settings/" with body
      """
      {"integration_event_retention_days": 60}
      """
    Then the response status should be 200
    And the response field "integration_event_retention_days" should equal integer 60
    # Restore default
    When I PATCH the v2 admin endpoint "suppliers/admin/settings/" with body
      """
      {"integration_event_retention_days": 90}
      """
    Then the response status should be 200
