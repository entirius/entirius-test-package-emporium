@suppliers @mapping-ux
Feature: Suppliers data-keys endpoint — feeds CMS mapping comboboxes
  As an operator wiring a new supplier mapping in the CMS
  I want to pick `source_field` from a combobox instead of typing JSON paths
  So that I stop hallucinating keys that don't exist in SupplierProduct.data.

  The endpoint returns 3 reserved tokens (__name__, __cost__, __ean__) plus
  every dot-path observed in SupplierProduct.data across a sample, each
  ranked by presence_pct.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @data-keys @auth
  Scenario: Endpoint requires authentication — leak protection
    # data-keys exposes the raw shape of a supplier's feed, not just metadata.
    # Without auth a competitor could enumerate fields. v2 contract: 401, never
    # an empty list, never a teaser payload.
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/data-keys/" without auth
    Then the response status should be 401

  @data-keys @tokens-only
  Scenario: Unknown supplier → 404 (not a silent empty payload)
    # We do not want operators staring at an empty combobox wondering whether
    # the supplier has no products or the idx is wrong. 404 means "look at the
    # URL", empty data_keys means "fetch the feed".
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/bdd-ghost-supplier/data-keys/"
    Then the response status should be 404

  @data-keys @shape
  Scenario: Happy-path — tokens always present, response shape matches contract
    # Even for a brand new supplier with no SupplierProducts yet, the 3
    # reserved tokens MUST be served so the operator can map __name__ /
    # __cost__ / __ean__ before the first feed run. data_keys is permitted
    # to be empty in that case; sample_size reflects the actual sample.
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/demo-supplier/data-keys/"
    Then the response status should be 200
    And the response field "tokens" should contain 3 items
    And the response field "data_keys" should be a list
    And the response field "sample_size" should not be null
