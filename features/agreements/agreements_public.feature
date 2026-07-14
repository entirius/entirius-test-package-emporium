@agreements @v2 @public
Feature: Agreements Public API v2
  As a storefront user
  I want to view agreement definitions and submit consents
  So that I can manage my consent preferences

  Background:
    Given the test package has been imported
    And the channel is the primary channel

  # --- Public Definitions ---

  Scenario: Public definitions accessible without auth
    When I GET the v2 admin endpoint "agreements/{channel_idx}/definitions/" without auth
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  Scenario: Public definitions filter by category
    When I GET the v2 admin endpoint "agreements/{channel_idx}/definitions/?category=mandatory" without auth
    Then the response status should be 200

  Scenario: Public definitions filter by language
    When I GET the v2 admin endpoint "agreements/{channel_idx}/definitions/?language=en" without auth
    Then the response status should be 200

  # --- Consent Submit ---

  Scenario: Submit consent without auth
    When I POST to the v2 public endpoint "agreements/{channel_idx}/consents/" with body
      """
      {
        "email": "bdd-test@example.com",
        "agreements": [
          {"slug": "terms-of-service", "granted": true},
          {"slug": "marketing-email", "granted": false}
        ],
        "source": "checkout"
      }
      """
    Then the response status should be 201

  Scenario: Check consent status via admin people detail
    Given I am authenticated as an admin user
    When I GET the v2 admin endpoint "agreements/admin/people/bdd-test@example.com/"
    Then the response status should be 200

  # --- Consent Withdraw ---

  Scenario: Withdraw consent requires authentication
    Given I am authenticated as an admin user
    When I POST to the v2 admin endpoint "agreements/{channel_idx}/consents/withdraw/" with body
      """
      {
        "slugs": ["marketing-email"]
      }
      """
    Then the response status should be 200
