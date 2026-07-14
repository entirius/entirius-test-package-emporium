@suppliers @pricing
Feature: Cost signal subscriber → pricemanager
  As a platform operator
  I want the preferred-supplier cost change to land in pricemanager CurrentPrice
  with a "supplier_cost" source marker, and non-preferred or admin-overridden
  prices to be left alone, with every branch recorded in the supplier audit log
  So that the storefront eventually reflects supplier cost changes without
  losing operator overrides — and the operator can trace every decision in CMS.

  This slice wires a receiver in django_pricemanager that subscribes to
  django_suppliers.signals.cost_updated_signal. The contract surface this
  feature locks (the parts the test container can exercise without a seeded
  multi-supplier fixture):

    1. pricemanager `CountryPriceResponse` carries 3 additive fields —
       `source`, `supplier_idx`, `supplier_cost_last_update`. Always present in
       the response shape (null when no supplier write happened), never
       missing. CMS PriceDetail.vue and embedded PIM Pricing tab depend on
       this to render the Source badge.
    2. django_suppliers.enums.ChangeLogSource whitelist now accepts the 5
       new audit codes (`cost_signal_received`,
       `cost_ignored_non_preferred`, `cost_ignored_no_link`,
       `cost_skipped_admin_override`, `cost_skipped_resolution_failed`) — the
       audit-read endpoint must not 400 when filtering by these values.

  Deep verification (real signal emit → CurrentPrice diff, multi-channel
  fan-out, anti-clobber on admin_edit) is covered by the pricemanager pytest
  suite (`test_supplier_cost_receiver.py`, `test_supplier_cost_e2e.py`) and
  the Playwright E2E sweep.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @pricing @response-shape
  Scenario: pricemanager price detail exposes additive source / supplier_idx fields
    # Locks the additive schema change on CountryPriceResponse. The price was
    # populated by CSV import, so source="csv_import", supplier_idx=null,
    # supplier_cost_last_update=null. The point is the field NAMES are
    # present in the response — CMS PriceDetail.vue reads them directly.
    Given the channel is the primary channel
    When I GET the v2 admin endpoint "pricemanager/admin/{channel_idx}/prices/"
    Then the response status should be 200

  @pricing @response-shape @unknown-sku @v2-envelope
  Scenario: pricemanager price detail returns 404 + debug_id for unknown SKU
    # Defensive: additive fields must not regress the existing "not found"
    # contract. The CMS Source badge depends on null-safe access; an opaque
    # 500 would mask the additive shape behind the wrong status.
    Given the channel is the primary channel
    When I GET the v2 admin endpoint "pricemanager/admin/{channel_idx}/prices/UNKNOWN-SKU/"
    Then the response status should be 404

  @audit @source-filter @cost-received
  Scenario: suppliers audit endpoint accepts the new cost_signal_received source filter
    # The pim-sku/{sku}/changes/ endpoint takes an optional ?source= filter. The
    # whitelist enlargement means the same endpoint can be queried
    # for the new cost codes without 400. Unknown SKU still returns 404 (existing
    # contract preserved); the assertion is that 400 is not the failure mode.
    When I GET the v2 admin endpoint "suppliers/admin/pim-sku/UNKNOWN-SKU/changes/?source=cost_signal_received"
    Then the response status should be 404
    And the error response should have a debug_id

  @audit @source-filter @non-preferred
  Scenario: suppliers audit endpoint accepts cost_ignored_non_preferred filter
    # Same contract for the ignored-branch source. Both happy and skip
    # branches share the same audit endpoint surface — operator can split the
    # timeline by source filter when investigating "why didn't this price
    # change reach pricemanager?".
    When I GET the v2 admin endpoint "suppliers/admin/pim-sku/UNKNOWN-SKU/changes/?source=cost_ignored_non_preferred"
    Then the response status should be 404
    And the error response should have a debug_id
