@contentdb @admin @delete
Feature: ContentDB Content DELETE — protected routes and system content
  As a CMS admin
  I want DELETE on protected drafts to fail with a readable 400 error
  So that I can distinguish "blocked by design" from a server crash

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: Unauthenticated DELETE returns 401
    When I DELETE the ContentDB admin endpoint "content/static-page/c0000001-0001-4000-8000-000000000001/" without auth
    Then the response status should be 401

  # @blocked-by-module: legacy DjangoAuth on the delete endpoints rejects the suite's JWT (401);
  # unblock = switch django-contentdb admin delete auth to JWT (then drop this tag).
  @blocked-by-module
  Scenario: Deleting the last home draft is blocked with 400
    When I DELETE the ContentDB admin endpoint "content/static-page/c0000001-0001-4000-8000-000000000001/"
    Then the response status should be 400
    And the response data list should contain "Cannot delete the last home page"

  # @blocked-by-module: legacy DjangoAuth on the delete endpoints rejects the suite's JWT (401);
  # unblock = switch django-contentdb admin delete auth to JWT (then drop this tag).
  @blocked-by-module
  Scenario: Deleting system content (megamenu header) is blocked with 400
    When I DELETE the ContentDB admin endpoint "layout-extender/header/c0000017-0001-4000-8000-000000000001/"
    Then the response status should be 400
    And the response data list should contain "Cannot delete system content"
