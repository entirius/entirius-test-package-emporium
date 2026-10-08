@access @access-security
Feature: Access security — sensitive routes need exactly their permission
  As the platform's security owner
  I want every sensitive admin route to ask for the permission the contract names, not just any valid one
  So that a wrong-but-valid area on a route (which the module ownership tests accept) fails here

  The caller is `norole` (staff, no role): the gate refuses every area route and names what it needs, read off the
  live route map. POST carries an empty JSON object and every id does not exist, so a wrongly admitted request meets
  the view's 400/404/405 and changes nothing.

  Background:
    Given the channel is the primary channel

  Scenario Outline: SR-01 <method> <path> needs "<needs>"
    Given the caller is norole
    When the caller sends <method> to "<path>"
    Then the answer is 403 with "ACCESS_DENIED"
    And the refusal names "<needs>"

    Examples: sensitive routes
      | method | path                                                                    | needs                            |
      | DELETE | api/pim/v2/admin/{channel_idx}/products/BDD-NO-SUCH-SKU/                | needs pim.product_delete:write   |
      | DELETE | api/pim/admin/{channel_idx}/products/BDD-NO-SUCH-SKU/                   | needs pim.product_delete:write   |
      | PATCH  | api/pim/v2/admin/{channel_idx}/products/BDD-NO-SUCH-SKU/                | needs pim.products:write         |
      | DELETE | api/pim/v2/admin/feature-sets/bdd-no-such-set/                          | needs pim.product_delete:write   |
      | DELETE | api/pim/admin/feature-sets/bdd-no-such-set/                             | needs pim.product_delete:write   |
      | PATCH  | api/pim/v2/admin/feature-sets/bdd-no-such-set/                          | needs pim.schema:write           |
      | POST   | api/atlas/v2/admin/realproducts/merge-by-ean/                           | needs pim.product_delete:write   |
      | POST   | api/suppliers/v2/admin/realproducts/merge-by-ean/                       | needs pim.product_delete:write   |
      | GET    | api/checkout/v2/admin/{channel_idx}/orders/                             | needs checkout.orders:read       |
      | GET    | api/agreements/v2/admin/marketing-subscribers/export/                   | needs agreements.consents:write  |
      | POST   | api/leads/v2/admin/gdpr/export/                                         | needs leads.gdpr:write           |
      | GET    | api-admin/contentdb/v1/content/bdd-ct/bdd-uid/published/                | needs content.publish:write      |
      | POST   | api/access/v2/admin/roles/                                              | needs access.manage:write        |
      | POST   | api/access/v2/admin/grants/                                             | needs access.manage:write        |
      | POST   | api/access/v2/admin/staff/                                              | needs access.manage:write        |
      | GET    | admin/                                                                  | superuser only                   |
      | POST   | api/communicator/v2/admin/{channel_idx}/templates/999999/test-generate/ | needs communicator.content:write |
