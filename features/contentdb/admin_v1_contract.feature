@contentdb @admin @auth
Feature: ContentDB Admin v1 authentication contract
  As the CMS talking to /api-admin/contentdb/v1/
  I want the admin API to accept my JWT and reject anonymous callers
  So that a misconfigured auth stack fails the suite instead of the panel

  # Regression guard: until django-contentdb 5.1.0 these endpoints authenticated
  # through DjangoAuth, which resolved the Bearer token via the service's
  # AUTHENTICATION_BACKENDS. A service without a JWT-reading backend answered 401
  # to every request and the CMS looked logged out. The public-API scenarios could
  # not see it — only an authenticated v1 call can.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  Scenario: Admin JWT is accepted on the channels endpoint
    When I GET the ContentDB admin endpoint "channels/"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Admin JWT is accepted on the languages endpoint
    When I GET the ContentDB admin endpoint "languages/"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Admin JWT is accepted on the content-types endpoint
    When I GET the ContentDB admin endpoint "content-types/"
    Then the response status should be 200
    And the response should contain at least 1 items

  Scenario: Anonymous read of channels is rejected
    When I GET the ContentDB admin endpoint "channels/" without auth
    Then the response status should be 401

  Scenario: Anonymous read of languages is rejected
    When I GET the ContentDB admin endpoint "languages/" without auth
    Then the response status should be 401

  Scenario: Anonymous read of content-types is rejected
    When I GET the ContentDB admin endpoint "content-types/" without auth
    Then the response status should be 401
