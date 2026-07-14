@suppliers @cms-panel
Feature: Suppliers audit log — CMS PIM panel bridge contract
  As a CMS PIM operator
  I want the PIM list view and detail view to safely consume the
  pim-sku bridge endpoints
  So that bulk "Updated" badges in the products list and the Supplier tab
  in product detail render without panel coupling to django_suppliers.

  This slice ships the CMS Blueprint side: a bulk has-changes call on the list
  view (one request per page) and a Supplier tab on detail view that calls
  changes, acknowledge, and force-repush. This feature locks the contract
  surface that the frontend depends on. Live data verification (badge visible
  with seeded SP + acknowledge round-trip) is exercised by the /browser skill
  scenario tracked separately because it requires pre-seeded
  ProductSupplierLink + SupplierProductChangeLog rows.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @bulk @badge-contract
  Scenario: Bulk has-changes contract holds for SKUs without any supplier links
    # CMS ProductList.fetchSupplierStatuses() calls this once per page of products.
    # Every requested SKU must appear in the response map regardless of whether a
    # ProductSupplierLink row exists. has_supplier=false short-circuits the badge
    # render without a per-SKU /changes/ call. If the contract slips and unknown
    # SKUs vanish from the response, the badge logic in ProductList.vue would
    # crash on undefined.unseen_count when iterating rows.
    When I GET the v2 admin endpoint "suppliers/admin/pim-sku/has-changes/?skus=BRIDGE-A,BRIDGE-B,BRIDGE-C"
    Then the response status should be 200
    And the response field "skus" should be a dict
    And the response nested field "skus.BRIDGE-A.has_supplier" should equal "False"
    And the response nested field "skus.BRIDGE-A.unseen_count" should equal integer 0
    And the response nested field "skus.BRIDGE-B.has_supplier" should equal "False"
    And the response nested field "skus.BRIDGE-C.has_supplier" should equal "False"

  @timeline @filter
  Scenario: Timeline endpoint accepts unseen_only query param without crashing on unknown SKU
    # The Supplier tab passes unseen_only=true when the "Unseen only" FilterChip is
    # active. The query param is forwarded to the service even when no SKU/SP
    # rows exist. The endpoint should still produce a v2-shaped 404 (unknown SKU)
    # rather than 400 (unknown param) — otherwise the CMS filter chip would have
    # to special-case unknown SKUs.
    When I GET the v2 admin endpoint "suppliers/admin/pim-sku/UNKNOWN-SKU/changes/?unseen_only=true"
    Then the response status should be 404
    And the error response should have a debug_id

  @acknowledge @validation
  Scenario: Acknowledge endpoint rejects empty payload with v2 envelope
    # CMS "Acknowledge all" button sends {"all_unseen": true}. If we ship a build
    # that accidentally sends an empty body, the response must remain a 400 with
    # debug_id (not 500) so the negative toast can surface a stable identifier.
    When I POST to the v2 admin endpoint "suppliers/admin/pim-sku/SOMESKU/acknowledge/" with body
      """
      {}
      """
    Then the response status should be 400
    And the error response should have a debug_id

  @force-repush @no-body
  Scenario: Force re-push tolerates empty body for unknown SKU
    # CMS Supplier tab sends an empty POST body (no payload, just the action).
    # Backend must accept the request and answer 404 for SKUs with no active
    # ProductSupplierLink — not 400. The frontend negative toast assumes the
    # error has a debug_id.
    When I POST to the v2 admin endpoint "suppliers/admin/pim-sku/UNKNOWN-SKU/force-repush/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id
