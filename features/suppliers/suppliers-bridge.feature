@suppliers @cms-panel
Feature: Suppliers panel bridge — CMS Suppliers panel contract
  As a CMS Suppliers operator
  I want the Suppliers panel Products tab and the SupplierReview "Updated"
  mode to talk to the existing v2 admin product endpoints
  So that the new Updated badge, the unseen filter, and the bulk
  force-repush / acknowledge actions work without any
  fresh contract drift from the existing pim-sku endpoints.

  This slice ships the symmetric CMS counterpart: a warning "Updated"
  badge on Products tab rows where data_changed_at > pushed_at, a "Has
  unseen changes" FilterChip, multi-select with a BulkActionBar (boot
  promoted in phase 1), a 4th "Updated" mode in SupplierReview, and a
  per-SP drawer with audit timeline + mapping context. All bulk handlers
  reuse the existing pim-sku endpoints — this file locks the contract surface the
  new UI depends on.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @products @list-ordering
  Scenario: Supplier products list accepts ordering=-data_changed_at without 400
    # UpdatedMode (SupplierReview 4th mode) issues GET_SupplierProducts({
    # status: 'pushed', ordering: '-data_changed_at', page_size: 100 }) and
    # then client-filters rows where data_changed_at > pushed_at. If the
    # backend ever rejected the ordering value as not-allowed, the UpdatedMode
    # would surface a negative toast and show empty state — regression bait.
    When I GET the v2 admin endpoint "suppliers/admin/products/?status=pushed&ordering=-data_changed_at&page_size=5"
    Then the response status should be 200
    And the response field "results" should be a list

  @products @bulk-has-changes
  Scenario: Bulk has-changes contract holds for pushed-only seed SKUs
    # ProductsTab in the Suppliers panel does not call has-changes today
    # (the per-SP data_changed_at > pushed_at signal is enough). UpdatedMode
    # MAY add a cross-supplier badge-by-SKU map in a follow-up. This locks
    # the pim-sku contract so we can lean on it later: every requested SKU
    # is present in the response, has_supplier=false for unknown SKUs,
    # unseen_count is always an integer (never null).
    When I GET the v2 admin endpoint "suppliers/admin/pim-sku/has-changes/?skus=SKU-X,SKU-Y"
    Then the response status should be 200
    And the response field "skus" should be a dict
    And the response nested field "skus.SKU-X.has_supplier" should equal "False"
    And the response nested field "skus.SKU-X.unseen_count" should equal integer 0
    And the response nested field "skus.SKU-Y.has_supplier" should equal "False"

  @bulk @per-sp-force-repush
  Scenario: Per-SP force-repush returns v2-shaped 404 for unknown PK
    # Bulk "Force re-push selected" in ProductsTab + UpdatedMode iterates
    # POST_ForceRepushProduct(sp.id). The composable swallows per-SP errors
    # into a failed[] array and surfaces them as a warning toast — but only
    # if the backend answers with a v2 envelope (debug_id). If the endpoint
    # ever returned 500 with str(exception) the toast would leak SQL fragments.
    When I POST to the v2 admin endpoint "suppliers/admin/products/9999999/force-repush/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id

  @bulk @per-sku-acknowledge
  Scenario: Per-SKU acknowledge with {"all_unseen": true} is idempotent for unknown SKUs
    # Bulk "Acknowledge selected" in ProductsTab + UpdatedMode dedupes
    # selected SP rows by real_product_sku and calls POST_AcknowledgeSku(sku,
    # {all_unseen: true}) for each unique SKU. The composable counts the SKU
    # as succeeded when the call returns 200; locking the idempotent
    # no-op contract here means a stale SKU (link removed mid-session) does
    # NOT trip the warning toast — the SKU is reported as "acknowledged"
    # with acknowledged_count=0 and the operator does not see a misleading
    # failure indicator.
    When I POST to the v2 admin endpoint "suppliers/admin/pim-sku/UNKNOWN-SKU/acknowledge/" with body
      """
      {"all_unseen": true}
      """
    Then the response status should be 200
    And the response field "sku" should equal "UNKNOWN-SKU"
    And the response field "acknowledged_count" should equal integer 0
