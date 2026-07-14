@suppliers @release-hygiene
Feature: Suppliers release hygiene — celery tasks load + qms_writer loads + munin maps qms
  As a platform operator
  I want a smoke check that the post-release suppliers stack still loads
  So that the celery task re-exports and the qms_writer signature cannot
  silently regress between releases — a broken import would 500 the admin API and a
  broken munin mapping would hide the Stock panel.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @celery
  Scenario: Suppliers admin list loads — proves celery task re-exports + signals import clean
    # `signals/handlers.py` imports `push_approved_for_supplier_task` from
    # `django_suppliers.tasks.push_pipeline`. If that re-export regressed and the task module
    # failed to register, apps.py would crash at startup and the suppliers admin
    # would 500. A clean 200 here is the smoke gate.
    When I GET the v2 admin endpoint "suppliers/admin/suppliers/"
    Then the response status should be 200
    And the response should have pagination fields
      | field    |
      | count    |
      | next     |
      | previous |
      | results  |

  @celery
  Scenario: Bulk push endpoint accepts empty payload — proves push pipeline imports clean
    # BulkPushView reaches into push_service which transitively imports the push
    # pipeline task module. A bad re-export would manifest as 500, not 400.
    # Empty body → push across all active suppliers; with the test package that
    # is a zero-op but the endpoint must still respond 200 with the counts shape.
    When I POST to the v2 admin endpoint "suppliers/admin/push/" with body
      """
      {}
      """
    Then the response status should be 200
    And the response field "suppliers_processed" should not be null
    And the response field "success" should not be null
    And the response field "failed" should not be null

  @cms
  Scenario: Munin module registry exposes qms — proves the qms mapping is registered
    # The CMS admin maps the munin module key `qms` to its stock panel.
    # The mapping is only useful if django-qms
    # is discoverable via munin. munin returns {platform, modules: {key: {...}}}
    # so we check the qms entry by nested-field path. Suppliers also asserted
    # to prove the suppliers module loads clean too.
    When I GET the v2 admin endpoint "munin/"
    Then the response status should be 200
    And the response nested field "modules.qms.label" should not be null
    And the response nested field "modules.suppliers.label" should not be null
