@atlas @v2 @push
Feature: Atlas Admin API -- push to PIM and EAN auto-match
  Push targets live on atl-push (feed-less, so nothing ever delists them).
  NOTE: the "Push an approved product" scenario is one-shot per database
  (approved -> pushed is one-way); a BDD re-run needs a fresh `make seed`.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Push an approved product creates its RealProduct
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value        |
      | source | atl-push     |
      | search | BDD-ATL-P001 |
    Then the response status should be 200
    And I save the first result field "id" as "sp_id"
    When I POST to the v2 admin endpoint "atlas/admin/products/{sp_id}/push/" with body
      """
      {}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "atlas/admin/products/{sp_id}/"
    Then the response status should be 200
    And the response field "status" should equal "pushed"
    And the response field "real_product_id" should not be null

  Scenario: Force-repush on a non-pushed product is refused
    When I GET the v2 admin endpoint "atlas/admin/products/" with params
      | param  | value        |
      | source | atl-push     |
      | search | BDD-ATL-P002 |
    Then I save the first result field "id" as "sp_id"
    When I POST to the v2 admin endpoint "atlas/admin/products/{sp_id}/force-repush/" with body
      """
      {}
      """
    Then the response status should be 400

  Scenario: Push without a warehouse leaves a qms warning event
    When I GET the v2 admin endpoint "atlas/admin/events/" with params
      | param      | value                        |
      | event_type | qms_warehouse_not_configured |
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: Auto-matched anchors carry their source links
    When I GET the v2 admin endpoint "atlas/admin/auto-matched/"
    Then the response status should be 200
    And the results should contain an item with "sku" equal to "ATL-ANCHOR-1"
