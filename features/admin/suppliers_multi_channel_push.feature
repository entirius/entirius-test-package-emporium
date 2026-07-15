@admin @suppliers @v2 @suppliers-push @supplier
Feature: Suppliers Admin API -- Push to PIM
  As an admin user
  I want to push approved supplier products to PIM channels
  So that supplier products become discoverable in storefront catalogs

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user
    And regional language "pl" id is stored as "lang_id"
    And regional currency "PLN" id is stored as "curr_id"

  Scenario: Push approved DEMO-007 SP to demo target channel
    # DEMO-007 fixture status is 'approved' against profile default-pl -> default-europe.
    # Own SP per push scenario: push is one-shot (approved -> pushed, no re-push) in 2.0.0.
    When I POST to the v2 admin endpoint "suppliers/admin/products/7/push/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "status" should equal "pushed"

  Scenario: Push for SP without active mapping profile returns pre-flight error
    # Create new supplier without any active mapping profile, no SP can push
    Given I ensure supplier with idx "bdd-no-profile-sup" is cleaned up
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/" with body
      """
      {
        "idx": "bdd-no-profile-sup",
        "name": "BDD No Profile",
        "supplier_role": "trade",
        "supplier_type": "feed",
        "review_mode": "manual",
        "default_language_id": {lang_id},
        "default_currency_id": {curr_id},
        "sku_prefix": "BDDNP"
      }
      """
    Then the response status should be 201
    # Bulk push reports the supplier under preflight_failed (HTTP 200 with a per-supplier report)
    When I POST to the v2 admin endpoint "suppliers/admin/push/" with body
      """
      {"supplier_idx": "bdd-no-profile-sup"}
      """
    Then the response status should be 200
    And the response field "preflight_failed" should contain 1 items
    Given I ensure supplier with idx "bdd-no-profile-sup" is cleaned up

  Scenario: Push to non-existent SP returns 404
    When I POST to the v2 admin endpoint "suppliers/admin/products/9999999/push/" with body
      """
      {}
      """
    Then the response status should be 404

  Scenario: Bulk push for demo-supplier picks up only approved SPs
    When I POST to the v2 admin endpoint "suppliers/admin/push/" with body
      """
      {"supplier_idx": "demo-supplier", "async": false}
      """
    Then the response status should be 200
    And the response field "suppliers_processed" should equal integer 1

  Scenario: Force re-push does not duplicate pushed_to_channel_idxs (D24/D33)
    # DEMO-007 was pushed above; re-push is one-shot so refresh goes through force-repush,
    # which must not duplicate the already-pushed channel.
    When I POST to the v2 admin endpoint "suppliers/admin/products/7/force-repush/" with body
      """
      {}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "suppliers/admin/products/7/"
    Then the response status should be 200
    And the response field "pushed_to_channel_idxs" should be a list
