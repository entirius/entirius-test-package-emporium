@atlas @v2 @duplicates
Feature: Atlas Admin API -- duplicate RealProducts and merge-by-EAN
  Seed leaves duplicate pairs: ATL-DUP-A1/A2 (weights within tolerance, merge
  suggestion) and ATL-DUP-B1/B2 (missing weight, review suggestion).
  NOTE: the happy-path merge is one-shot per database (the loser is re-pointed);
  a BDD re-run needs a fresh `make seed`.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Merge with mismatched EANs is refused
    When I POST to the v2 admin endpoint "atlas/admin/realproducts/merge-by-ean/" with body
      """
      {"winner_sku": "ATL-DUP-A1", "loser_sku": "ATL-DUP-B1", "reason": "bdd invalid merge"}
      """
    Then the response status should be 400

  Scenario: Merge without a reason is refused
    When I POST to the v2 admin endpoint "atlas/admin/realproducts/merge-by-ean/" with body
      """
      {"winner_sku": "ATL-DUP-A1", "loser_sku": "ATL-DUP-A2", "reason": ""}
      """
    Then the response status should be 400

  Scenario: Merging the within-tolerance pair succeeds
    When I POST to the v2 admin endpoint "atlas/admin/realproducts/merge-by-ean/" with body
      """
      {"winner_sku": "ATL-DUP-A1", "loser_sku": "ATL-DUP-A2", "reason": "bdd duplicate cleanup"}
      """
    Then the response status should be 200
    When I GET the v2 admin endpoint "atlas/admin/duplicates/"
    Then the response status should be 200
    And the results count should be greater than 0
