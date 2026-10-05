@access @admin @v2
Feature: Access roles — what each staff role may read and write
  As a shop operator
  I want every admin route to answer by the caller's role
  So that viewers read, editors edit content and only managers delete products

  Scenario: A-01 the viewer reads PIM features
    Given I am authenticated as the viewer staff user
    When I GET the v2 admin endpoint "pim/admin/features/"
    Then the response status should be 200

  Scenario: A-02 the viewer cannot create a PIM feature
    Given I am authenticated as the viewer staff user
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {}
      """
    Then the gate refuses with issue "ACCESS_DENIED"
    And the error response should have a debug_id

  Scenario: A-03 the editor passes the gate on PIM features and the view validates the body
    Given I am authenticated as the editor staff user
    When I POST to the v2 admin endpoint "pim/admin/features/" with body
      """
      {}
      """
    Then the response status should be 400
    And the response is not a gate refusal

  Scenario: A-04 the editor cannot create a tax class
    Given I am authenticated as the editor staff user
    When I POST to the v2 admin endpoint "pricemanager/admin/tax-classes/" with body
      """
      {}
      """
    Then the gate refuses with issue "ACCESS_DENIED"

  Scenario: A-05 the manager cannot read access roles
    Given I am authenticated as the manager staff user
    When I GET the v2 admin endpoint "access/admin/roles/"
    Then the gate refuses with issue "ACCESS_DENIED"
    And the refusal names "access.manage"

  Scenario: A-06 a customer account is refused on an admin route without naming an area
    Given I am authenticated as a regular user
    When I GET the v2 admin endpoint "pim/admin/features/"
    Then the gate refuses with issue "STAFF_ONLY"
    And the refusal names "A staff account is required."

  Scenario: A-07 an anonymous admin request is still a 401
    When I GET the v2 admin endpoint "pim/admin/features/" without auth
    Then the response status should be 401
    And the error response should have error code "AUTHENTICATION_REQUIRED"

  Scenario: A-08 an unknown admin path stays a 404
    Given I am authenticated as the viewer staff user
    When I GET the unknown v2 admin path "pim/admin/no-such-route-bdd-access/"
    Then the response status should be 404

  Scenario: A-09 me lists the viewer's read permissions and no access management
    Given I am authenticated as the viewer staff user
    When I GET the v2 admin endpoint "access/me/"
    Then the response status should be 200
    And the permission "pim.products" should be "read"
    And the permission "access.manage" should be absent
    And the response field "manages_access" should be false

  Scenario: A-10 only the manager deletes a SKU the editor created and edited
    Given the channel is the primary channel
    And a run-unique suffix is saved as "saved.run"
    And the admin sends DELETE to "pim/admin/{channel_idx}/products/BDD-ACCESS-{saved.run}/" when the scenario ends
    And I am authenticated as the editor staff user
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {"sku": "BDD-ACCESS-{saved.run}", "feature_set_idx": "default", "visibility": 4, "is_enabled": true, "product_class": 1, "kind_of_product": 0}
      """
    Then the response status should be 201
    When I PATCH the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-ACCESS-{saved.run}/" with body
      """
      {"visibility": 2}
      """
    Then the response status should be 200
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-ACCESS-{saved.run}/"
    Then the gate refuses with issue "ACCESS_DENIED"
    And the refusal names "pim.product_delete:write"
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-ACCESS-{saved.run}/"
    Then the response status should be 200
    Given I am authenticated as the manager staff user
    When I DELETE the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-ACCESS-{saved.run}/"
    Then the response status should be 200
    When I GET the unknown v2 admin path "pim/admin/{channel_idx}/products/BDD-ACCESS-{saved.run}/"
    Then the response status should be 404

  Scenario: A-11 me shows SKU delete for the manager only
    Given I am authenticated as the editor staff user
    When I GET the v2 admin endpoint "access/me/"
    Then the permission "pim.product_delete" should be absent
    Given I am authenticated as the manager staff user
    When I GET the v2 admin endpoint "access/me/"
    Then the permission "pim.product_delete" should be "write"

  Scenario: A-12 only the manager deletes a feature set that still has products
    # Deleting a feature set cascades to every product of the set in every channel: it is a SKU delete.
    Given the channel is the primary channel
    And a run-unique suffix is saved as "saved.run"
    And the admin sends DELETE to "pim/admin/{channel_idx}/products/BDD-ACCESS-FS-{saved.run}/" when the scenario ends
    And the admin sends DELETE to "pim/admin/feature-sets/bdd-access-fs-{saved.run}/" when the scenario ends
    And I am authenticated as the editor staff user
    When I POST to the v2 admin endpoint "pim/admin/feature-sets/" with body
      """
      {"idx": "bdd-access-fs-{saved.run}", "name": "BDD access feature set"}
      """
    Then the response status should be 201
    When I POST to the v2 admin endpoint "pim/admin/{channel_idx}/products/" with body
      """
      {"sku": "BDD-ACCESS-FS-{saved.run}", "feature_set_idx": "bdd-access-fs-{saved.run}", "visibility": 4, "is_enabled": true, "product_class": 1, "kind_of_product": 0}
      """
    Then the response status should be 201
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-access-fs-{saved.run}/"
    Then the gate refuses with issue "ACCESS_DENIED"
    And the refusal names "needs pim.product_delete:write"
    When I GET the v2 admin endpoint "pim/admin/{channel_idx}/products/BDD-ACCESS-FS-{saved.run}/"
    Then the response status should be 200
    Given I am authenticated as the manager staff user
    When I DELETE the v2 admin endpoint "pim/admin/feature-sets/bdd-access-fs-{saved.run}/"
    Then the response status should be 200
    When I GET the unknown v2 admin path "pim/admin/{channel_idx}/products/BDD-ACCESS-FS-{saved.run}/"
    Then the response status should be 404

  Scenario Outline: A-13 the editor cannot delete a SKU through <route>
    # The SKU does not exist and the merge body is empty: a wrongly admitted request meets the view's 400/404.
    Given the channel is the primary channel
    And the caller is editor
    When the caller sends <method> to "<path>"
    Then the answer is 403 with "ACCESS_DENIED"
    And the refusal names "needs pim.product_delete:write"

    Examples: SKU-deleting routes
      | route                      | method | path                                                  |
      | the legacy PIM root        | DELETE | api/pim/admin/{channel_idx}/products/BDD-NO-SUCH-SKU/ |
      | the atlas merge-by-ean     | POST   | api/atlas/v2/admin/realproducts/merge-by-ean/         |
      | the suppliers merge-by-ean | POST   | api/suppliers/v2/admin/realproducts/merge-by-ean/     |

  @blocked-by-module
  Scenario: A-14 the viewer cannot start a paid AI test generation
    # Blocked by django_communicator: TemplateTestGenerateView declares access_levels {"POST": "read"}, which wins
    # over the access defaults (test-generate is no longer a POST-read there). Drop the tag once the view follows.
    Given the channel is the primary channel
    And the caller is viewer
    When the caller sends POST to "api/communicator/v2/admin/{channel_idx}/templates/999999/test-generate/"
    Then the answer is 403 with "ACCESS_DENIED"
    And the refusal names "needs communicator.content:write"
