@access @access-security
Feature: Access security — principal × route class × method
  As the platform's security owner
  I want every caller to get exactly the contract's answer on every class of admin route
  So that no role, customer or API token reaches more than it was given

  Rows: anonymous, a customer (`testuser`), staff without a role (`norole`), the Viewer, Editor and Manager role
  users, `accessadmin` (Administrator role, not superuser), the superuser and a token-only caller (a fresh publishable
  token in X-API-KEY plus a fresh secret token in X-API-ADMIN-KEY, no JWT — always the anonymous answer, D12).
  POST carries an empty JSON object; DELETE targets an id that does not exist, so a wrongly admitted write meets the
  view's 400/404/405 and nothing is created or deleted. Issue `-` = no gate issue in the body, `n/a` = HEAD (no body).

  Background:
    Given the channel is the primary channel

  Scenario Outline: PM-01 admin area (pim.schema) — <principal> <method>
    # Editor and up pass the gate: the view validates the empty body (400) or finds no such feature (404).
    Given the caller is <principal>
    When the caller sends <method> to "<path>"
    Then the answer is <status> with "<issue>"

    Examples: admin area (pim.schema)
      | principal   | method  | path                                           | status | issue         |
      | anonymous   | GET     | api/pim/v2/admin/features/                     | 401    | -             |
      | anonymous   | HEAD    | api/pim/v2/admin/features/                     | 401    | n/a           |
      | anonymous   | OPTIONS | api/pim/v2/admin/features/                     | 401    | -             |
      | anonymous   | POST    | api/pim/v2/admin/features/                     | 401    | -             |
      | anonymous   | DELETE  | api/pim/v2/admin/features/bdd-no-such-feature/ | 401    | -             |
      | customer    | GET     | api/pim/v2/admin/features/                     | 403    | STAFF_ONLY    |
      | customer    | HEAD    | api/pim/v2/admin/features/                     | 403    | n/a           |
      | customer    | OPTIONS | api/pim/v2/admin/features/                     | 403    | STAFF_ONLY    |
      | customer    | POST    | api/pim/v2/admin/features/                     | 403    | STAFF_ONLY    |
      | customer    | DELETE  | api/pim/v2/admin/features/bdd-no-such-feature/ | 403    | STAFF_ONLY    |
      | norole      | GET     | api/pim/v2/admin/features/                     | 403    | ACCESS_DENIED |
      | norole      | HEAD    | api/pim/v2/admin/features/                     | 403    | n/a           |
      | norole      | OPTIONS | api/pim/v2/admin/features/                     | 403    | ACCESS_DENIED |
      | norole      | POST    | api/pim/v2/admin/features/                     | 403    | ACCESS_DENIED |
      | norole      | DELETE  | api/pim/v2/admin/features/bdd-no-such-feature/ | 403    | ACCESS_DENIED |
      | viewer      | GET     | api/pim/v2/admin/features/                     | 200    | -             |
      | viewer      | HEAD    | api/pim/v2/admin/features/                     | 200    | n/a           |
      | viewer      | OPTIONS | api/pim/v2/admin/features/                     | 200    | -             |
      | viewer      | POST    | api/pim/v2/admin/features/                     | 403    | ACCESS_DENIED |
      | viewer      | DELETE  | api/pim/v2/admin/features/bdd-no-such-feature/ | 403    | ACCESS_DENIED |
      | editor      | GET     | api/pim/v2/admin/features/                     | 200    | -             |
      | editor      | HEAD    | api/pim/v2/admin/features/                     | 200    | n/a           |
      | editor      | OPTIONS | api/pim/v2/admin/features/                     | 200    | -             |
      | editor      | POST    | api/pim/v2/admin/features/                     | 400    | -             |
      | editor      | DELETE  | api/pim/v2/admin/features/bdd-no-such-feature/ | 404    | -             |
      | manager     | GET     | api/pim/v2/admin/features/                     | 200    | -             |
      | manager     | HEAD    | api/pim/v2/admin/features/                     | 200    | n/a           |
      | manager     | OPTIONS | api/pim/v2/admin/features/                     | 200    | -             |
      | manager     | POST    | api/pim/v2/admin/features/                     | 400    | -             |
      | manager     | DELETE  | api/pim/v2/admin/features/bdd-no-such-feature/ | 404    | -             |
      | accessadmin | GET     | api/pim/v2/admin/features/                     | 200    | -             |
      | accessadmin | HEAD    | api/pim/v2/admin/features/                     | 200    | n/a           |
      | accessadmin | OPTIONS | api/pim/v2/admin/features/                     | 200    | -             |
      | accessadmin | POST    | api/pim/v2/admin/features/                     | 400    | -             |
      | accessadmin | DELETE  | api/pim/v2/admin/features/bdd-no-such-feature/ | 404    | -             |
      | admin       | GET     | api/pim/v2/admin/features/                     | 200    | -             |
      | admin       | HEAD    | api/pim/v2/admin/features/                     | 200    | n/a           |
      | admin       | OPTIONS | api/pim/v2/admin/features/                     | 200    | -             |
      | admin       | POST    | api/pim/v2/admin/features/                     | 400    | -             |
      | admin       | DELETE  | api/pim/v2/admin/features/bdd-no-such-feature/ | 404    | -             |
      | token-only  | GET     | api/pim/v2/admin/features/                     | 401    | -             |
      | token-only  | HEAD    | api/pim/v2/admin/features/                     | 401    | n/a           |
      | token-only  | OPTIONS | api/pim/v2/admin/features/                     | 401    | -             |
      | token-only  | POST    | api/pim/v2/admin/features/                     | 401    | -             |
      | token-only  | DELETE  | api/pim/v2/admin/features/bdd-no-such-feature/ | 401    | -             |

  Scenario Outline: PM-02 PII area (checkout.orders) — <principal> <method>
    # Viewer and Editor read orders but never write them; Manager and up reach the view, which has no POST/DELETE (405).
    Given the caller is <principal>
    When the caller sends <method> to "<path>"
    Then the answer is <status> with "<issue>"

    Examples: PII area (checkout.orders)
      | principal   | method  | path                                                          | status | issue         |
      | anonymous   | GET     | api/checkout/v2/admin/{channel_idx}/orders/                   | 401    | -             |
      | anonymous   | HEAD    | api/checkout/v2/admin/{channel_idx}/orders/                   | 401    | n/a           |
      | anonymous   | OPTIONS | api/checkout/v2/admin/{channel_idx}/orders/                   | 401    | -             |
      | anonymous   | POST    | api/checkout/v2/admin/{channel_idx}/orders/                   | 401    | -             |
      | anonymous   | DELETE  | api/checkout/v2/admin/{channel_idx}/orders/bdd-no-such-order/ | 401    | -             |
      | customer    | GET     | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | STAFF_ONLY    |
      | customer    | HEAD    | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | n/a           |
      | customer    | OPTIONS | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | STAFF_ONLY    |
      | customer    | POST    | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | STAFF_ONLY    |
      | customer    | DELETE  | api/checkout/v2/admin/{channel_idx}/orders/bdd-no-such-order/ | 403    | STAFF_ONLY    |
      | norole      | GET     | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | ACCESS_DENIED |
      | norole      | HEAD    | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | n/a           |
      | norole      | OPTIONS | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | ACCESS_DENIED |
      | norole      | POST    | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | ACCESS_DENIED |
      | norole      | DELETE  | api/checkout/v2/admin/{channel_idx}/orders/bdd-no-such-order/ | 403    | ACCESS_DENIED |
      | viewer      | GET     | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | viewer      | HEAD    | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | n/a           |
      | viewer      | OPTIONS | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | viewer      | POST    | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | ACCESS_DENIED |
      | viewer      | DELETE  | api/checkout/v2/admin/{channel_idx}/orders/bdd-no-such-order/ | 403    | ACCESS_DENIED |
      | editor      | GET     | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | editor      | HEAD    | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | n/a           |
      | editor      | OPTIONS | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | editor      | POST    | api/checkout/v2/admin/{channel_idx}/orders/                   | 403    | ACCESS_DENIED |
      | editor      | DELETE  | api/checkout/v2/admin/{channel_idx}/orders/bdd-no-such-order/ | 403    | ACCESS_DENIED |
      | manager     | GET     | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | manager     | HEAD    | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | n/a           |
      | manager     | OPTIONS | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | manager     | POST    | api/checkout/v2/admin/{channel_idx}/orders/                   | 405    | -             |
      | manager     | DELETE  | api/checkout/v2/admin/{channel_idx}/orders/bdd-no-such-order/ | 405    | -             |
      | accessadmin | GET     | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | accessadmin | HEAD    | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | n/a           |
      | accessadmin | OPTIONS | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | accessadmin | POST    | api/checkout/v2/admin/{channel_idx}/orders/                   | 405    | -             |
      | accessadmin | DELETE  | api/checkout/v2/admin/{channel_idx}/orders/bdd-no-such-order/ | 405    | -             |
      | admin       | GET     | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | admin       | HEAD    | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | n/a           |
      | admin       | OPTIONS | api/checkout/v2/admin/{channel_idx}/orders/                   | 200    | -             |
      | admin       | POST    | api/checkout/v2/admin/{channel_idx}/orders/                   | 405    | -             |
      | admin       | DELETE  | api/checkout/v2/admin/{channel_idx}/orders/bdd-no-such-order/ | 405    | -             |
      | token-only  | GET     | api/checkout/v2/admin/{channel_idx}/orders/                   | 401    | -             |
      | token-only  | HEAD    | api/checkout/v2/admin/{channel_idx}/orders/                   | 401    | n/a           |
      | token-only  | OPTIONS | api/checkout/v2/admin/{channel_idx}/orders/                   | 401    | -             |
      | token-only  | POST    | api/checkout/v2/admin/{channel_idx}/orders/                   | 401    | -             |
      | token-only  | DELETE  | api/checkout/v2/admin/{channel_idx}/orders/bdd-no-such-order/ | 401    | -             |

  Scenario Outline: PM-03 GET PII export (agreements.consents, write) — <principal> <method>
    # A GET PII export counts as a write: Viewer and Editor are refused (OPTIONS stays a read and answers the metadata).
    Given the caller is <principal>
    When the caller sends <method> to "<path>"
    Then the answer is <status> with "<issue>"

    Examples: GET PII export (agreements.consents, write)
      | principal   | method  | path                                                  | status | issue         |
      | anonymous   | GET     | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | -             |
      | anonymous   | HEAD    | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | n/a           |
      | anonymous   | OPTIONS | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | -             |
      | anonymous   | POST    | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | -             |
      | anonymous   | DELETE  | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | -             |
      | customer    | GET     | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | STAFF_ONLY    |
      | customer    | HEAD    | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | n/a           |
      | customer    | OPTIONS | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | STAFF_ONLY    |
      | customer    | POST    | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | STAFF_ONLY    |
      | customer    | DELETE  | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | STAFF_ONLY    |
      | norole      | GET     | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | norole      | HEAD    | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | n/a           |
      | norole      | OPTIONS | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | norole      | POST    | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | norole      | DELETE  | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | viewer      | GET     | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | viewer      | HEAD    | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | n/a           |
      | viewer      | OPTIONS | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | -             |
      | viewer      | POST    | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | viewer      | DELETE  | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | editor      | GET     | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | editor      | HEAD    | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | n/a           |
      | editor      | OPTIONS | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | -             |
      | editor      | POST    | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | editor      | DELETE  | api/agreements/v2/admin/marketing-subscribers/export/ | 403    | ACCESS_DENIED |
      | manager     | GET     | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | -             |
      | manager     | HEAD    | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | n/a           |
      | manager     | OPTIONS | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | -             |
      | manager     | POST    | api/agreements/v2/admin/marketing-subscribers/export/ | 405    | -             |
      | manager     | DELETE  | api/agreements/v2/admin/marketing-subscribers/export/ | 405    | -             |
      | accessadmin | GET     | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | -             |
      | accessadmin | HEAD    | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | n/a           |
      | accessadmin | OPTIONS | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | -             |
      | accessadmin | POST    | api/agreements/v2/admin/marketing-subscribers/export/ | 405    | -             |
      | accessadmin | DELETE  | api/agreements/v2/admin/marketing-subscribers/export/ | 405    | -             |
      | admin       | GET     | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | -             |
      | admin       | HEAD    | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | n/a           |
      | admin       | OPTIONS | api/agreements/v2/admin/marketing-subscribers/export/ | 200    | -             |
      | admin       | POST    | api/agreements/v2/admin/marketing-subscribers/export/ | 405    | -             |
      | admin       | DELETE  | api/agreements/v2/admin/marketing-subscribers/export/ | 405    | -             |
      | token-only  | GET     | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | -             |
      | token-only  | HEAD    | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | n/a           |
      | token-only  | OPTIONS | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | -             |
      | token-only  | POST    | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | -             |
      | token-only  | DELETE  | api/agreements/v2/admin/marketing-subscribers/export/ | 401    | -             |

  Scenario Outline: PM-04 staff baseline (regional reference list) — <principal> <method>
    # Every active staff user reaches the regional lists without a grant; a customer does not.
    Given the caller is <principal>
    When the caller sends <method> to "<path>"
    Then the answer is <status> with "<issue>"

    Examples: staff baseline (regional reference list)
      | principal   | method  | path                             | status | issue      |
      | anonymous   | GET     | api/regional/v2/admin/countries/ | 401    | -          |
      | anonymous   | HEAD    | api/regional/v2/admin/countries/ | 401    | n/a        |
      | anonymous   | OPTIONS | api/regional/v2/admin/countries/ | 401    | -          |
      | anonymous   | POST    | api/regional/v2/admin/countries/ | 401    | -          |
      | anonymous   | DELETE  | api/regional/v2/admin/countries/ | 401    | -          |
      | customer    | GET     | api/regional/v2/admin/countries/ | 403    | STAFF_ONLY |
      | customer    | HEAD    | api/regional/v2/admin/countries/ | 403    | n/a        |
      | customer    | OPTIONS | api/regional/v2/admin/countries/ | 403    | STAFF_ONLY |
      | customer    | POST    | api/regional/v2/admin/countries/ | 403    | STAFF_ONLY |
      | customer    | DELETE  | api/regional/v2/admin/countries/ | 403    | STAFF_ONLY |
      | norole      | GET     | api/regional/v2/admin/countries/ | 200    | -          |
      | norole      | HEAD    | api/regional/v2/admin/countries/ | 200    | n/a        |
      | norole      | OPTIONS | api/regional/v2/admin/countries/ | 200    | -          |
      | norole      | POST    | api/regional/v2/admin/countries/ | 405    | -          |
      | norole      | DELETE  | api/regional/v2/admin/countries/ | 405    | -          |
      | viewer      | GET     | api/regional/v2/admin/countries/ | 200    | -          |
      | viewer      | HEAD    | api/regional/v2/admin/countries/ | 200    | n/a        |
      | viewer      | OPTIONS | api/regional/v2/admin/countries/ | 200    | -          |
      | viewer      | POST    | api/regional/v2/admin/countries/ | 405    | -          |
      | viewer      | DELETE  | api/regional/v2/admin/countries/ | 405    | -          |
      | editor      | GET     | api/regional/v2/admin/countries/ | 200    | -          |
      | editor      | HEAD    | api/regional/v2/admin/countries/ | 200    | n/a        |
      | editor      | OPTIONS | api/regional/v2/admin/countries/ | 200    | -          |
      | editor      | POST    | api/regional/v2/admin/countries/ | 405    | -          |
      | editor      | DELETE  | api/regional/v2/admin/countries/ | 405    | -          |
      | manager     | GET     | api/regional/v2/admin/countries/ | 200    | -          |
      | manager     | HEAD    | api/regional/v2/admin/countries/ | 200    | n/a        |
      | manager     | OPTIONS | api/regional/v2/admin/countries/ | 200    | -          |
      | manager     | POST    | api/regional/v2/admin/countries/ | 405    | -          |
      | manager     | DELETE  | api/regional/v2/admin/countries/ | 405    | -          |
      | accessadmin | GET     | api/regional/v2/admin/countries/ | 200    | -          |
      | accessadmin | HEAD    | api/regional/v2/admin/countries/ | 200    | n/a        |
      | accessadmin | OPTIONS | api/regional/v2/admin/countries/ | 200    | -          |
      | accessadmin | POST    | api/regional/v2/admin/countries/ | 405    | -          |
      | accessadmin | DELETE  | api/regional/v2/admin/countries/ | 405    | -          |
      | admin       | GET     | api/regional/v2/admin/countries/ | 200    | -          |
      | admin       | HEAD    | api/regional/v2/admin/countries/ | 200    | n/a        |
      | admin       | OPTIONS | api/regional/v2/admin/countries/ | 200    | -          |
      | admin       | POST    | api/regional/v2/admin/countries/ | 405    | -          |
      | admin       | DELETE  | api/regional/v2/admin/countries/ | 405    | -          |
      | token-only  | GET     | api/regional/v2/admin/countries/ | 401    | -          |
      | token-only  | HEAD    | api/regional/v2/admin/countries/ | 401    | n/a        |
      | token-only  | OPTIONS | api/regional/v2/admin/countries/ | 401    | -          |
      | token-only  | POST    | api/regional/v2/admin/countries/ | 401    | -          |
      | token-only  | DELETE  | api/regional/v2/admin/countries/ | 401    | -          |

  Scenario Outline: PM-05 access.manage (access roles) — <principal> <method>
    # Only the built-in Administrator role and the superuser manage access.
    Given the caller is <principal>
    When the caller sends <method> to "<path>"
    Then the answer is <status> with "<issue>"

    Examples: access.manage (access roles)
      | principal   | method  | path                                 | status | issue         |
      | anonymous   | GET     | api/access/v2/admin/roles/           | 401    | -             |
      | anonymous   | HEAD    | api/access/v2/admin/roles/           | 401    | n/a           |
      | anonymous   | OPTIONS | api/access/v2/admin/roles/           | 401    | -             |
      | anonymous   | POST    | api/access/v2/admin/roles/           | 401    | -             |
      | anonymous   | DELETE  | api/access/v2/admin/roles/999999999/ | 401    | -             |
      | customer    | GET     | api/access/v2/admin/roles/           | 403    | STAFF_ONLY    |
      | customer    | HEAD    | api/access/v2/admin/roles/           | 403    | n/a           |
      | customer    | OPTIONS | api/access/v2/admin/roles/           | 403    | STAFF_ONLY    |
      | customer    | POST    | api/access/v2/admin/roles/           | 403    | STAFF_ONLY    |
      | customer    | DELETE  | api/access/v2/admin/roles/999999999/ | 403    | STAFF_ONLY    |
      | norole      | GET     | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | norole      | HEAD    | api/access/v2/admin/roles/           | 403    | n/a           |
      | norole      | OPTIONS | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | norole      | POST    | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | norole      | DELETE  | api/access/v2/admin/roles/999999999/ | 403    | ACCESS_DENIED |
      | viewer      | GET     | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | viewer      | HEAD    | api/access/v2/admin/roles/           | 403    | n/a           |
      | viewer      | OPTIONS | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | viewer      | POST    | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | viewer      | DELETE  | api/access/v2/admin/roles/999999999/ | 403    | ACCESS_DENIED |
      | editor      | GET     | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | editor      | HEAD    | api/access/v2/admin/roles/           | 403    | n/a           |
      | editor      | OPTIONS | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | editor      | POST    | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | editor      | DELETE  | api/access/v2/admin/roles/999999999/ | 403    | ACCESS_DENIED |
      | manager     | GET     | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | manager     | HEAD    | api/access/v2/admin/roles/           | 403    | n/a           |
      | manager     | OPTIONS | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | manager     | POST    | api/access/v2/admin/roles/           | 403    | ACCESS_DENIED |
      | manager     | DELETE  | api/access/v2/admin/roles/999999999/ | 403    | ACCESS_DENIED |
      | accessadmin | GET     | api/access/v2/admin/roles/           | 200    | -             |
      | accessadmin | HEAD    | api/access/v2/admin/roles/           | 200    | n/a           |
      | accessadmin | OPTIONS | api/access/v2/admin/roles/           | 200    | -             |
      | accessadmin | POST    | api/access/v2/admin/roles/           | 400    | -             |
      | accessadmin | DELETE  | api/access/v2/admin/roles/999999999/ | 404    | -             |
      | admin       | GET     | api/access/v2/admin/roles/           | 200    | -             |
      | admin       | HEAD    | api/access/v2/admin/roles/           | 200    | n/a           |
      | admin       | OPTIONS | api/access/v2/admin/roles/           | 200    | -             |
      | admin       | POST    | api/access/v2/admin/roles/           | 400    | -             |
      | admin       | DELETE  | api/access/v2/admin/roles/999999999/ | 404    | -             |
      | token-only  | GET     | api/access/v2/admin/roles/           | 401    | -             |
      | token-only  | HEAD    | api/access/v2/admin/roles/           | 401    | n/a           |
      | token-only  | OPTIONS | api/access/v2/admin/roles/           | 401    | -             |
      | token-only  | POST    | api/access/v2/admin/roles/           | 401    | -             |
      | token-only  | DELETE  | api/access/v2/admin/roles/999999999/ | 401    | -             |

  Scenario Outline: PM-06 Django admin (superusers only, Bearer JWT) — <principal> <method>
    # D32: the gate admits only a superuser's Bearer JWT; the admin site itself wants a session and redirects to its login. Every role is refused, Administrator included; the login page stays on the staff baseline. Writes without a CSRF token are refused before any view.
    Given the caller is <principal>
    When the caller sends <method> to "<path>"
    Then the answer is <status> with "<issue>"

    Examples: Django admin (superusers only, Bearer JWT)
      | principal   | method  | path         | status | issue          |
      | anonymous   | GET     | admin/       | 302    | login redirect |
      | anonymous   | HEAD    | admin/       | 302    | n/a            |
      | anonymous   | OPTIONS | admin/       | 302    | login redirect |
      | anonymous   | POST    | admin/       | 403    | -              |
      | anonymous   | DELETE  | admin/       | 403    | -              |
      | customer    | GET     | admin/       | 403    | STAFF_ONLY     |
      | customer    | HEAD    | admin/       | 403    | n/a            |
      | customer    | OPTIONS | admin/       | 403    | STAFF_ONLY     |
      | customer    | POST    | admin/       | 403    | -              |
      | customer    | DELETE  | admin/       | 403    | -              |
      | norole      | GET     | admin/       | 403    | ACCESS_DENIED  |
      | norole      | HEAD    | admin/       | 403    | n/a            |
      | norole      | OPTIONS | admin/       | 403    | ACCESS_DENIED  |
      | norole      | POST    | admin/       | 403    | -              |
      | norole      | DELETE  | admin/       | 403    | -              |
      | viewer      | GET     | admin/       | 403    | ACCESS_DENIED  |
      | viewer      | HEAD    | admin/       | 403    | n/a            |
      | viewer      | OPTIONS | admin/       | 403    | ACCESS_DENIED  |
      | viewer      | POST    | admin/       | 403    | -              |
      | viewer      | DELETE  | admin/       | 403    | -              |
      | editor      | GET     | admin/       | 403    | ACCESS_DENIED  |
      | editor      | HEAD    | admin/       | 403    | n/a            |
      | editor      | OPTIONS | admin/       | 403    | ACCESS_DENIED  |
      | editor      | POST    | admin/       | 403    | -              |
      | editor      | DELETE  | admin/       | 403    | -              |
      | manager     | GET     | admin/       | 403    | ACCESS_DENIED  |
      | manager     | HEAD    | admin/       | 403    | n/a            |
      | manager     | OPTIONS | admin/       | 403    | ACCESS_DENIED  |
      | manager     | POST    | admin/       | 403    | -              |
      | manager     | DELETE  | admin/       | 403    | -              |
      | accessadmin | GET     | admin/       | 403    | ACCESS_DENIED  |
      | accessadmin | HEAD    | admin/       | 403    | n/a            |
      | accessadmin | OPTIONS | admin/       | 403    | ACCESS_DENIED  |
      | accessadmin | POST    | admin/       | 403    | -              |
      | accessadmin | DELETE  | admin/       | 403    | -              |
      | accessadmin | GET     | admin/login/ | 200    | -              |
      | accessadmin | HEAD    | admin/login/ | 200    | n/a            |
      | admin       | GET     | admin/       | 302    | login redirect |
      | admin       | HEAD    | admin/       | 302    | n/a            |
      | admin       | OPTIONS | admin/       | 302    | login redirect |
      | admin       | POST    | admin/       | 403    | -              |
      | admin       | DELETE  | admin/       | 403    | -              |
      | token-only  | GET     | admin/       | 302    | login redirect |
      | token-only  | HEAD    | admin/       | 302    | n/a            |
      | token-only  | OPTIONS | admin/       | 302    | login redirect |
      | token-only  | POST    | admin/       | 403    | -              |
      | token-only  | DELETE  | admin/       | 403    | -              |

  Scenario Outline: PM-07 admin_not_self_auth (contentdb router root) — <principal> <method>
    # The router root authenticates on Session + Basic only, so a Bearer JWT is no principal there: the gate answers 401 itself.
    Given the caller is <principal>
    When the caller sends <method> to "<path>"
    Then the answer is <status> with "<issue>"

    Examples: admin_not_self_auth (contentdb router root)
      | principal   | method  | path                    | status | issue             |
      | anonymous   | GET     | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | anonymous   | HEAD    | api-admin/contentdb/v1/ | 401    | n/a               |
      | anonymous   | OPTIONS | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | anonymous   | POST    | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | anonymous   | DELETE  | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | customer    | GET     | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | customer    | HEAD    | api-admin/contentdb/v1/ | 401    | n/a               |
      | customer    | OPTIONS | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | customer    | POST    | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | customer    | DELETE  | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | norole      | GET     | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | norole      | HEAD    | api-admin/contentdb/v1/ | 401    | n/a               |
      | norole      | OPTIONS | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | norole      | POST    | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | norole      | DELETE  | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | viewer      | GET     | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | viewer      | HEAD    | api-admin/contentdb/v1/ | 401    | n/a               |
      | viewer      | OPTIONS | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | viewer      | POST    | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | viewer      | DELETE  | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | editor      | GET     | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | editor      | HEAD    | api-admin/contentdb/v1/ | 401    | n/a               |
      | editor      | OPTIONS | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | editor      | POST    | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | editor      | DELETE  | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | manager     | GET     | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | manager     | HEAD    | api-admin/contentdb/v1/ | 401    | n/a               |
      | manager     | OPTIONS | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | manager     | POST    | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | manager     | DELETE  | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | accessadmin | GET     | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | accessadmin | HEAD    | api-admin/contentdb/v1/ | 401    | n/a               |
      | accessadmin | OPTIONS | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | accessadmin | POST    | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | accessadmin | DELETE  | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | admin       | GET     | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | admin       | HEAD    | api-admin/contentdb/v1/ | 401    | n/a               |
      | admin       | OPTIONS | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | admin       | POST    | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | admin       | DELETE  | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | token-only  | GET     | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | token-only  | HEAD    | api-admin/contentdb/v1/ | 401    | n/a               |
      | token-only  | OPTIONS | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | token-only  | POST    | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |
      | token-only  | DELETE  | api-admin/contentdb/v1/ | 401    | NOT_AUTHENTICATED |

  Scenario Outline: PM-08 unknown admin path — <principal> <method>
    # The gate resolves first: an unknown admin path is a 404 for everybody.
    Given the caller is <principal>
    When the caller sends <method> to "<path>"
    Then the answer is <status> with "<issue>"

    Examples: unknown admin path
      | principal   | method  | path                                | status | issue |
      | anonymous   | GET     | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | anonymous   | HEAD    | api/pim/v2/admin/bdd-no-such-route/ | 404    | n/a   |
      | anonymous   | OPTIONS | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | anonymous   | POST    | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | anonymous   | DELETE  | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | customer    | GET     | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | customer    | HEAD    | api/pim/v2/admin/bdd-no-such-route/ | 404    | n/a   |
      | customer    | OPTIONS | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | customer    | POST    | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | customer    | DELETE  | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | norole      | GET     | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | norole      | HEAD    | api/pim/v2/admin/bdd-no-such-route/ | 404    | n/a   |
      | norole      | OPTIONS | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | norole      | POST    | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | norole      | DELETE  | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | viewer      | GET     | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | viewer      | HEAD    | api/pim/v2/admin/bdd-no-such-route/ | 404    | n/a   |
      | viewer      | OPTIONS | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | viewer      | POST    | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | viewer      | DELETE  | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | editor      | GET     | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | editor      | HEAD    | api/pim/v2/admin/bdd-no-such-route/ | 404    | n/a   |
      | editor      | OPTIONS | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | editor      | POST    | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | editor      | DELETE  | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | manager     | GET     | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | manager     | HEAD    | api/pim/v2/admin/bdd-no-such-route/ | 404    | n/a   |
      | manager     | OPTIONS | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | manager     | POST    | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | manager     | DELETE  | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | accessadmin | GET     | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | accessadmin | HEAD    | api/pim/v2/admin/bdd-no-such-route/ | 404    | n/a   |
      | accessadmin | OPTIONS | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | accessadmin | POST    | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | accessadmin | DELETE  | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | admin       | GET     | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | admin       | HEAD    | api/pim/v2/admin/bdd-no-such-route/ | 404    | n/a   |
      | admin       | OPTIONS | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | admin       | POST    | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | admin       | DELETE  | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | token-only  | GET     | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | token-only  | HEAD    | api/pim/v2/admin/bdd-no-such-route/ | 404    | n/a   |
      | token-only  | OPTIONS | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | token-only  | POST    | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |
      | token-only  | DELETE  | api/pim/v2/admin/bdd-no-such-route/ | 404    | -     |

  Scenario Outline: PM-09 Django admin with a session — <principal>
    # D32 (replaces operator Q1): the admin site is for superusers only; the Administrator role signs in (staff baseline) but gets 403.
    Given the caller has a Django admin session as <principal>
    When the caller sends GET to "admin/"
    Then the answer is <status> with "<issue>"

    Examples: Django admin index over a session login
      | principal   | status | issue         |
      | admin       | 200    | -             |
      | accessadmin | 403    | ACCESS_DENIED |
      | manager     | 403    | ACCESS_DENIED |
      | editor      | 403    | ACCESS_DENIED |
      | viewer      | 403    | ACCESS_DENIED |
      | norole      | 403    | ACCESS_DENIED |
