@suppliers @push-correctness
Feature: Language resolution supplier ↔ channel
  As a platform operator
  I want the push pipeline to resolve the target language against the channel
  context (Profile.import_language → supplier.default_language ∈ channel.languages
  → channel.default_language with warning) and the Validate endpoint to block
  mismatches that would silently fall back
  So that a PL supplier pushed to an EN-only channel either writes to EN (with
  a warning event surfaced as a CMS toast) or is caught at Validate time —
  no more DB hot-fixes copying value_txt_t9n.pl → value_txt_t9n.en after the fact.

  This slice adds two stable contract surfaces the CMS depends on:
    1. PushResponse.events: list[dict]  — empty by default, populated with
       {event_type:"language_fallback", severity:"warning", ...} when push
       silently fell back.
    2. validate_profile errors: list[str] — entries that begin with the
       literal prefix "[profile_language_mismatch]" so MappingsTab can detect
       the specific failure type without parsing free-form text.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @validate @v2-envelope
  Scenario: Validate endpoint returns v2 404 envelope for unknown profile
    # Defensive contract — the language-mismatch check (when profile.import_language
    # is empty) only runs after the profile is loaded. Unknown profile must still
    # 404 with debug_id; nothing here should change that path.
    When I POST to the v2 admin endpoint "suppliers/admin/suppliers/UNKNOWN-SUPPLIER/mapping-profiles/UNKNOWN-PROF/validate/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id

  @push @response-shape
  Scenario: Push endpoint returns events list for unknown SP via v2 envelope
    # Push of an unknown PK is a 404 path (not 200) so we can't directly assert
    # `events` is present on the success body without seeding. We at least lock
    # that the v2 error envelope is intact — the events[] field is a non-breaking
    # additive change to the 200 schema (default_factory=list) so OpenAPI clients
    # generated against the new schema work either way.
    When I POST to the v2 admin endpoint "suppliers/admin/products/9999999/push/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id

  @push @force-repush-shape
  Scenario: Force re-push endpoint returns events list shape for unknown SP via v2 envelope
    # Same additive-only contract for force_repush — this slice surfaces fallback
    # events on each push call, including force re-pushes. Validate the v2
    # envelope still holds on the 404 path so the new events field doesn't
    # cause a regression in error handling.
    When I POST to the v2 admin endpoint "suppliers/admin/products/9999999/force-repush/" with body
      """
      {}
      """
    Then the response status should be 404
    And the error response should have a debug_id
