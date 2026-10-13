@siteintel
Feature: Siteintel — domain audits from recorded sources
  As a module that needs intel about a shop's website
  I want one call to return a cleaned snapshot per source, reused while the audit is valid
  So that no domain is fetched twice and every consumer reads the same result

  Data: fixtures/django_siteintel.cfg.yaml (dummy API keys). zeno points PSI and urlscan at the recordings
  in fixtures/siteintel/ (recording mode: desktop PSI only, mobile is "unavailable"); the heuristic source
  fetches fixtures/siteintel/sites/ through the `fixtures` container. Audits are finished by the
  development endpoint test/run-now/ — no waiting. "No valid siteintel audit is cached" expires every valid
  audit against a far-future clock (test/expire-now/), so the file re-runs on one seed. The three synthetic
  sites share the host `fixtures` — one registrable domain — so S-08 expires between sites: the worker
  finishes an audit within a second and the next request would reuse it (S-01).

  Background:
    Given I am authenticated as an admin user
    And no valid siteintel audit is cached

  Scenario: S-01 a valid audit of the domain is reused — same id, no new fetch
    When I POST to the v2 admin endpoint "siteintel/admin/default-europe/audits/" with body
      """
      {"domain_or_url": "example-shop-1.test", "requested_by": "bdd:s-01"}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.s01"
    When the audit test run of "saved.s01" has completed
    Then the response field "status" should equal "partially_completed"
    And the report for source "lighthouse" should have status "completed"
    And the report for source "lighthouse" should have processed field "strategies.desktop.scores.performance" set
    And the report for source "lighthouse" should have processed field "strategies.mobile" equal to "unavailable"
    And the report for source "urlscan" should have processed field "page.domain" equal to "example-shop-1.test"
    When I POST to the v2 admin endpoint "siteintel/admin/default-europe/audits/" with body
      """
      {"domain_or_url": "https://www.example-shop-1.test/pl", "requested_by": "bdd:s-01-again"}
      """
    Then the response status should be 200
    And the response field "id" should equal "{saved.s01}"

  Scenario: S-08 the heuristic source tells the three synthetic sites apart
    When I POST to the v2 admin endpoint "siteintel/admin/default-europe/audits/" with body
      """
      {"domain_or_url": "http://fixtures:8000/fixtures/siteintel/sites/good/index.html", "requested_by": "bdd:s-08"}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.good"
    Given no valid siteintel audit is cached
    When I POST to the v2 admin endpoint "siteintel/admin/default-europe/audits/" with body
      """
      {"domain_or_url": "http://fixtures:8000/fixtures/siteintel/sites/slow/index.html", "requested_by": "bdd:s-08"}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.slow"
    Given no valid siteintel audit is cached
    When I POST to the v2 admin endpoint "siteintel/admin/default-europe/audits/" with body
      """
      {"domain_or_url": "http://fixtures:8000/fixtures/siteintel/sites/broken/index.html", "requested_by": "bdd:s-08"}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.broken"
    When the audit test run of "saved.good" has completed
    Then the report for source "heuristic" should have processed field "images_without_alt" equal to "0"
    And the report for source "heuristic" should have processed field "has_viewport_meta" equal to "true"
    When the audit test run of "saved.slow" has completed
    Then the report for source "heuristic" should have processed field "images_without_alt" equal to "20"
    And the report for source "heuristic" should have processed field "inline_script_count" equal to "6"
    When the audit test run of "saved.broken" has completed
    Then the report for source "heuristic" should have processed field "title" equal to "null"
    And the report for source "heuristic" should have processed field "images_without_alt" equal to "0"

  Scenario: S-09 a re-audit refreshes the reports of the same audit
    When I POST to the v2 admin endpoint "siteintel/admin/default-europe/audits/" with body
      """
      {"domain_or_url": "example-shop-2.test", "requested_by": "bdd:s-09"}
      """
    Then the response status should be 201
    And I save the response field "id" as "saved.s09"
    When the audit test run of "saved.s09" has completed
    Then I save the modified_at of the report for source "lighthouse" as "saved.s09_report"
    When I POST to the v2 admin endpoint "siteintel/admin/default-europe/audits/{saved.s09}/rerun/" with body
      """
      {"requested_by": "bdd:s-09-rerun"}
      """
    Then the response status should be 202
    And the response field "id" should equal "{saved.s09}"
    And the response field "status" should equal "pending"
    When the audit test run of "saved.s09" has completed
    Then the response field "id" should equal "{saved.s09}"
    And the report for source "lighthouse" was modified after "saved.s09_report"
