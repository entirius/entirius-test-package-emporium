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
  # Since entirius-django-agreements 3.0.1 the write needs the storefront's X-API-KEY or a JWT, and a key alone
  # (the body email is only a claim) may not grant or withdraw a marketing consent: that goes through newsletter
  # subscribe (double opt-in) or a signed-in customer.

  Scenario: Submit consent without auth is refused
    When I POST to the v2 public endpoint "agreements/{channel_idx}/consents/" with body
      """
      {
        "email": "bdd-test@example.com",
        "agreements": [{"slug": "terms-of-service", "granted": true}],
        "source": "checkout"
      }
      """
    Then the response status should be 401
    And the error response should have error code "AUTHENTICATION_REQUIRED"

  Scenario: Submit consent with the storefront key
    When I POST to the v2 public endpoint "agreements/{channel_idx}/consents/" with the storefront agreements key and body
      """
      {
        "email": "bdd-test@example.com",
        "agreements": [{"slug": "terms-of-service", "granted": true}],
        "source": "checkout"
      }
      """
    Then the response status should be 201

  Scenario Outline: A key-only caller cannot <action> a marketing consent
    When I POST to the v2 public endpoint "agreements/{channel_idx}/consents/" with the storefront agreements key and body
      """
      {
        "email": "bdd-test@example.com",
        "agreements": [
          {"slug": "terms-of-service", "granted": true},
          {"slug": "marketing-email", "granted": <granted>}
        ],
        "source": "checkout"
      }
      """
    Then the response status should be 400
    And the error response should have error code "INVALID_REQUEST"

    Examples:
      | action   | granted |
      | grant    | true    |
      | withdraw | false   |

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
