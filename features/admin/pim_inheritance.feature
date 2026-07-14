@admin @pim-admin @v2 @inheritance
Feature: PIM Admin API -- Translation Inheritance
  As a PIM admin
  I want to manage translation inheritance between channels
  So that products on secondary channels can share translations from the default channel

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @channels
  Scenario: Channel response includes languages and is_default
    When I GET "/api/pim/v2/admin/channels/"
    Then the response status is 200
    And each channel result has field "languages"
    And each channel result has field "is_default"
    And exactly one channel has "is_default" equal to true

  @inheritance @enable
  Scenario: Enable inheritance on secondary channel product
    Given product "TEST-INHERIT-001" exists on the default channel
    And product "TEST-INHERIT-001" exists on channel "default-europe"
    When I PATCH "/api/pim/v2/admin/default-europe/products/TEST-INHERIT-001/" with:
      | inherit_descriptions | true |
    Then the response status is 200
    And the response field "inherit_descriptions" is true
    And the response field "default_channel_idx" is not null

  @inheritance @copy
  Scenario: Copy translations from default channel (all matching)
    Given product "TEST-INHERIT-001" exists on the default channel with name "Default Name"
    And product "TEST-INHERIT-001" exists on channel "default-europe"
    When I POST "/api/pim/v2/admin/default-europe/products/TEST-INHERIT-001/copy-translations/" with JSON:
      """
      {"source_channel_idx": "{default_channel_idx}"}
      """
    Then the response status is 200

  @inheritance @copy
  Scenario: Copy translations from default channel (main language only)
    Given product "TEST-INHERIT-001" exists on the default channel
    And product "TEST-INHERIT-001" exists on channel "default-europe"
    When I POST "/api/pim/v2/admin/default-europe/products/TEST-INHERIT-001/copy-translations/" with JSON:
      """
      {
        "source_channel_idx": "{default_channel_idx}",
        "languages": ["en"]
      }
      """
    Then the response status is 200

  @inheritance @add-to-channel
  Scenario: Add product to secondary channel with inheritance
    Given product "TEST-INHERIT-BDD-002" exists on the default channel only
    When I POST "/api/pim/v2/admin/{default_channel_idx}/products/TEST-INHERIT-BDD-002/add-to-channel/" with JSON:
      """
      {
        "target_channel_idx": "default-europe",
        "copy_content": false,
        "inherit_descriptions": true
      }
      """
    Then the response status is 201
    And the response field "inherit_descriptions" is true

  @inheritance @add-to-channel @error
  Scenario: Add product to channel where it already exists returns 409
    Given product "TEST-INHERIT-001" exists on the default channel
    And product "TEST-INHERIT-001" exists on channel "default-europe"
    When I POST "/api/pim/v2/admin/{default_channel_idx}/products/TEST-INHERIT-001/add-to-channel/" with JSON:
      """
      {
        "target_channel_idx": "default-europe"
      }
      """
    Then the response status is 409

  @inheritance @toggle
  Scenario: Toggle language override on inherited attribute
    # Dedicated product: toggle needs a local override attribute, which would otherwise block
    # re-enabling inheritance on the shared TEST-INHERIT-001 in a re-run without reseed.
    Given product "TEST-INHERIT-OVR-001" on "default-europe" has description inheritance enabled
    When I POST "/api/pim/v2/admin/default-europe/products/TEST-INHERIT-OVR-001/toggle-override/" with JSON:
      """
      {
        "feature_idx": "name",
        "language": "en",
        "override": true
      }
      """
    Then the response status is 200

  @inheritance @propagation
  Scenario: Default channel product update succeeds when inheriting product exists
    Given product "TEST-INHERIT-001" on "default-europe" inherits from default
    When I PATCH the default channel product "TEST-INHERIT-001" name to "Updated Name"
    Then the response status is 200
    When I GET "/api/pim/v2/admin/{default_channel_idx}/products/TEST-INHERIT-001/"
    Then the response status is 200
    And the product name contains "Updated Name"

  @inheritance @auth
  Scenario: Non-admin user gets 403 on inheritance endpoints
    Given I am authenticated as a regular user
    When I POST "/api/pim/v2/admin/default-europe/products/TEST-INHERIT-001/copy-translations/" with JSON:
      """
      {"source_channel_idx": "default-test"}
      """
    Then the response status is 403
