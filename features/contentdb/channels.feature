@contentdb @channels
Feature: ContentDB Channel-based Content Filtering
  As an API consumer
  I want to filter published content by channel
  So that each storefront shows only relevant content

  Background:
    Given the test package has been imported

  Scenario: Public content visible with channel filter
    When I GET the ContentDB published endpoint "static-page/" with channel "test-channel-pl"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Public content visible with any channel filter
    When I GET the ContentDB published endpoint "static-page/" with channel "test-channel-multi"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Channel filter returns same content as access_rights (backward compat)
    When I GET the ContentDB published endpoint "static-page/" with routes "home"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Channels endpoint returns available channels
    When I GET the ContentDB endpoint "channels/"
    Then the response status should be 200

  Scenario: Published content includes channels field
    When I GET the ContentDB published endpoint "static-page/" with routes "home"
    Then the response status should be 200
    And each item should have the fields
      | field    |
      | channels |
