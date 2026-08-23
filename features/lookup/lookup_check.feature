@lookup
Feature: Lookup — cross-catalog duplicate detection
  As a catalog operator
  I want the lookup module to score and explain duplicate candidates across PIM and atlas
  So that I never create or approve the same product twice

  Data: fixtures/lookup/ (scripts/generate-lookup-fixtures.py), seeded by scripts/seed-lookup.py
  (seed.sh Step 6z). This file proves the flow runs end to end (test-strategy.md §5) — it does not
  assert a specific decision per pair class; that calibration lives in `lookup_eval` (numbers) and
  in the lookup module's own golden-pair tests (`tests/test_calibration_fixture_pairs.py`, mirroring
  the same fixture pairs: multipack, dirty_ean, name_only, photo_lookalike). `exact_dup` and
  `variant` have equivalents there too (`test_check_on_a_seeded_ean_decides_match`,
  `test_colour_variant_is_review_not_match`).

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

  Scenario: An image-only search returns a ranked candidate list with reasons
    Given I use the lookup fixture image "exact_dup-00-pim.png"
    When I POST an image to the lookup admin endpoint "search/"
    Then the response status should be 200
    And the response field "hits" should be a list

  Scenario: An image-only check of a look-alike photo never promotes to match (photo_lookalike)
    # The image-only guard (research r01 §2/§3): a candidate whose only positive evidence is its
    # picture is flagged `image_only` and can never reach `match`, whatever it looks like. This pair
    # shares its photo template with an unrelated product on purpose (different brand/name/GTIN) —
    # see generate-lookup-fixtures.py `_make_photo_lookalike`.
    Given I use the lookup fixture image "photo_lookalike-00-pim.png"
    When I POST an image to the lookup admin endpoint "check/"
    Then the response status should be 200
    And the response field "decision" should not equal "match"

  Scenario: Creating a PIM product with a duplicate EAN surfaces the atlas candidate
    # Reuses the exact_dup pair at index 2 (scripts/seed-lookup.py CREATE_HOOK_PAIR_INDEX) — its EAN
    # already exists on atl-lookup-a:EXACT-02, so a brand-new PIM product sharing it must come back
    # with that candidate in `possible_duplicates`.
    Given I ensure v2 admin resource "pim/admin/{channel_idx}/products/BDD-LKP-DUPCHECK/" is deleted
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {"sku": "BDD-LKP-DUPCHECK", "ean": "5900010000029", "feature_set_idx": "furniture",
       "attributes": [{"feature_idx": "name", "value_txt_t9n": {"en": "BDD duplicate-check product"}}]}
      """
    Then the response status should be 201
    And the response field "possible_duplicates" should contain a candidate for "LKP-PIM-EXACT-02"

  Scenario: Check without a token is rejected
    When I POST to the v2 public endpoint "lookup/admin/check/" with body
      """
      {"ean": "5900010000005"}
      """
    Then the response status should be 401

  Scenario: Search without a token is rejected
    When I POST to the v2 public endpoint "lookup/admin/search/" with body
      """
      {"ean": "5900010000005"}
      """
    Then the response status should be 401

  @lookup-oneshot
  Scenario: Accepting a duplicate-in-pim proposal links the SourceProduct
    # Consumes the exact_dup pair at index 1 (scripts/seed-lookup.py PROPOSAL_PAIR_INDEX), which
    # seed-lookup.py hands to enrichment as a pending duplicate_in_pim proposal.
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
