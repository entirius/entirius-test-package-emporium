@lookup
Feature: Lookup — cross-catalog duplicate detection
  As a catalog operator
  I want the lookup module to score and explain duplicate candidates across PIM and atlas
  So that I never create or approve the same product twice

  Data: fixtures/lookup/ (scripts/generate-lookup-fixtures.py), seeded by scripts/seed-lookup.py
  (seed.sh Step 6z). Pair classes: exact_dup, variant, multipack, dirty_ean, name_only,
  photo_lookalike — every class appears at least once below. Decisions asserted here are the
  measured engine output on the seeded fixture (test-strategy.md §4/§5): BDD proves the flow runs,
  it does not tune thresholds — `lookup_eval` is where precision/recall live.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: An exact EAN match resolves to a match decision (exact_dup)
    When I POST to the v2 admin endpoint "lookup/admin/check/" with body
      """
      {"ean": "5900010000005", "scope": ["atlas_source_product"]}
      """
    Then the response status should be 200
    And the response field "decision" should equal "match"
    And the response field "candidates" should contain a candidate for "atl-lookup-a:EXACT-00"

  Scenario: A colour variant with a shared MPN resolves to review, never match (variant)
    When I POST to the v2 admin endpoint "lookup/admin/check/" with body
      """
      {"name": "Talveri Backpack black", "brand": "Talveri", "mpn": "MOD-00", "scope": ["atlas_source_product"]}
      """
    Then the response status should be 200
    And the response field "decision" should equal "review"
    And the response field "candidates" should contain a candidate for "atl-lookup-a:VARIANT-00"

  Scenario: A single unit vs a 3-pack of the same name never matches on weight (multipack)
    When I POST to the v2 admin endpoint "lookup/admin/check/" with body
      """
      {"name": "Boreal Desk Lamp", "brand": "Boreal", "attrs": {"weight": "0.4"}, "scope": ["atlas_source_product"]}
      """
    Then the response status should be 200
    And the response field "decision" should equal "no_match"

  Scenario: A dirty brand on a shared GTIN caps the verdict at review (dirty_ean)
    When I POST to the v2 admin endpoint "lookup/admin/check/" with body
      """
      {"ean": "5900010000500", "brand": "Boreal", "scope": ["atlas_source_product"]}
      """
    Then the response status should be 200
    And the response field "decision" should equal "review"
    And the response field "candidates" should contain a candidate for "atl-lookup-a:DIRTY-00"

  Scenario: A name-only match with weight in tolerance is reviewable without any identifier (name_only)
    When I POST to the v2 admin endpoint "lookup/admin/check/" with body
      """
      {"name": "Sundrift Office Chair Edition", "brand": "Sundrift", "attrs": {"weight": "0.3"}, "scope": ["atlas_source_product"]}
      """
    Then the response status should be 200
    And the response field "decision" should equal "review"

  Scenario: Two unrelated products never match on identifiers alone (photo_lookalike)
    When I POST to the v2 admin endpoint "lookup/admin/check/" with body
      """
      {"ean": "5900010000609", "scope": ["atlas_source_product"]}
      """
    Then the response status should be 200
    And the response field "decision" should equal "no_match"

  Scenario: An image-only search returns a ranked candidate list with reasons
    Given I use the lookup fixture image "exact_dup-00-pim.png"
    When I POST an image to the lookup admin endpoint "search/"
    Then the response status should be 200
    And the response field "hits" should be a list

  Scenario: Creating a PIM product with a duplicate EAN surfaces the atlas candidate
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/products/BDD-LKP-DUPCHECK/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {"sku": "BDD-LKP-DUPCHECK", "ean": "5900010000029", "feature_set_idx": "furniture",
       "attributes": [{"feature_idx": "name", "value_txt_t9n": {"en": "BDD duplicate-check product"}}]}
      """
    Then the response status should be 201
    And the response field "possible_duplicates" should contain a candidate for "LKP-PIM-EXACT-02"

  @lookup-oneshot
  Scenario: Accepting a duplicate-in-pim proposal links the SourceProduct
    When I GET the v2 admin endpoint "enrichment/admin/proposals/" with params
      | param         | value   |
      | target_module | atlas   |
      | status        | pending |
    Then the response status should be 200
    And I save the first result field "id" as "saved.proposal_id"
    When I POST to the v2 admin endpoint "enrichment/admin/proposals/{saved.proposal_id}/accept/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "status" should equal "applied"
