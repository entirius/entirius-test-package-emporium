@spec-first @contact-forms @ads-conversions @admin @v2
Feature: Contact Forms — Admin Offline Conversion Queue (v2.1.0)
  As an operator
  I want to inspect and retry queued offline conversions
  So that I can recover from upload failures without waiting for the next batch

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user
    And the global ContactFormsSettings has google_ads_enabled=true
    And the channel has a GoogleAdsConfig with enabled=true and conversion-action ids set

  Scenario: List requires authentication
    When I GET the v2 admin endpoint "contact-forms/admin/offline-conversions/" without auth
    Then the response status should be 401

  Scenario: List returns rows scoped to channel
    Given a Lead with gclid is transitioned to "qualified"
    When I GET the v2 admin endpoint "contact-forms/admin/offline-conversions/?channel={channel_idx}"
    Then the response status should be 200
    And the results count should be greater than 0

  Scenario: Filter by status returns matching rows only
    Given a Lead with gclid is transitioned to "qualified"
    When I GET the v2 admin endpoint "contact-forms/admin/offline-conversions/?status=pending"
    Then the response status should be 200
    And every result should have "status" equal to "pending"

  Scenario: Retry resets a failed row to PENDING
    Given an OfflineConversionQueue row in status "failed"
    When I POST the v2 admin endpoint "contact-forms/admin/offline-conversions/{row_id}/retry/"
    Then the response status should be 200
    And the response should have "status" equal to "pending"
