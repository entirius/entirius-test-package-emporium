@access @access-security
Feature: Access security — public and key routes answer shoppers as before
  As a shopper or a storefront integration
  I want the shop's public, customer and key routes to answer exactly as they did before the access gate
  So that adding the gate changed nothing outside the admin set

  One route per module and audience of the plan-10 route map (`non_admin`), each called anonymously, as a customer
  (`testuser`) and with `Authorization: Bearer not-a-jwt`. The status column is what the route answered before the
  gate (plan 11's full BDD under the gate is the proof it did not change); a view that lists JWTAuthentication answers
  the bad Bearer with its own 401. No body anywhere carries a gate issue. Key routes get the right key — the checkout
  and contact-forms fixture keys (imported legacy tokens), or a fresh token of the route's scope where the seed has no
  key — and the `absent` text is the route's own key refusal, which must not appear.

  Background:
    Given the channel is the primary channel

  Scenario Outline: PR-01 public routes — <module> as <caller>
    Given the caller is <caller>
    And the caller presents the <key> key
    When the caller sends <method> to "<path>" with JSON <body>
    Then the answer is <status> with "-"
    And the answer does not contain "<absent>"

    Examples: public lists and anonymous endpoints
      | module                   | caller     | method | path                                                    | key | body | status | absent |
      | contentdb                | anonymous  | GET    | api/contentdb/v1/channels/                              | -   | -    | 200    | -      |
      | contentdb                | customer   | GET    | api/contentdb/v1/channels/                              | -   | -    | 200    | -      |
      | contentdb                | bad-bearer | GET    | api/contentdb/v1/channels/                              | -   | -    | 200    | -      |
      | faq                      | anonymous  | GET    | api/faq/v2/{channel_idx}/items/                         | -   | -    | 200    | -      |
      | faq                      | customer   | GET    | api/faq/v2/{channel_idx}/items/                         | -   | -    | 200    | -      |
      | faq                      | bad-bearer | GET    | api/faq/v2/{channel_idx}/items/                         | -   | -    | 200    | -      |
      | deliverypoints           | anonymous  | GET    | api/deliverypoints/v2/{channel_idx}/types/              | -   | -    | 200    | -      |
      | deliverypoints           | customer   | GET    | api/deliverypoints/v2/{channel_idx}/types/              | -   | -    | 200    | -      |
      | deliverypoints           | bad-bearer | GET    | api/deliverypoints/v2/{channel_idx}/types/              | -   | -    | 200    | -      |
      | agreements               | anonymous  | GET    | api/agreements/v2/{channel_idx}/definitions/            | -   | -    | 200    | -      |
      | agreements               | customer   | GET    | api/agreements/v2/{channel_idx}/definitions/            | -   | -    | 200    | -      |
      | agreements               | bad-bearer | GET    | api/agreements/v2/{channel_idx}/definitions/            | -   | -    | 401    | -      |
      | munin                    | anonymous  | GET    | api/munin/v2/                                           | -   | -    | 200    | -      |
      | munin                    | customer   | GET    | api/munin/v2/                                           | -   | -    | 200    | -      |
      | munin                    | bad-bearer | GET    | api/munin/v2/                                           | -   | -    | 401    | -      |
      | matrix v2                | anonymous  | GET    | api/matrix/v2/{channel_idx}/products/                   | -   | -    | 200    | -      |
      | matrix v2                | customer   | GET    | api/matrix/v2/{channel_idx}/products/                   | -   | -    | 200    | -      |
      | matrix v2                | bad-bearer | GET    | api/matrix/v2/{channel_idx}/products/                   | -   | -    | 200    | -      |
      | matrix v1                | anonymous  | GET    | api/matrix/v1/{channel_idx}/products/                   | -   | -    | 200    | -      |
      | matrix v1                | customer   | GET    | api/matrix/v1/{channel_idx}/products/                   | -   | -    | 200    | -      |
      | matrix v1                | bad-bearer | GET    | api/matrix/v1/{channel_idx}/products/                   | -   | -    | 200    | -      |
      | reviews                  | anonymous  | GET    | api/reviews/v1/{channel_idx}/reviews/                   | -   | -    | 400    | -      |
      | reviews                  | customer   | GET    | api/reviews/v1/{channel_idx}/reviews/                   | -   | -    | 400    | -      |
      | reviews                  | bad-bearer | GET    | api/reviews/v1/{channel_idx}/reviews/                   | -   | -    | 400    | -      |
      | staff login              | anonymous  | POST   | api/token/                                              | -   | {}   | 400    | -      |
      | staff login              | customer   | POST   | api/token/                                              | -   | {}   | 400    | -      |
      | staff login              | bad-bearer | POST   | api/token/                                              | -   | {}   | 400    | -      |
      | accounts                 | anonymous  | POST   | api/accounts/v1/{channel_idx}/customer/tokens/validate/ | -   | {}   | 200    | -      |
      | accounts                 | customer   | POST   | api/accounts/v1/{channel_idx}/customer/tokens/validate/ | -   | {}   | 200    | -      |
      | accounts                 | bad-bearer | POST   | api/accounts/v1/{channel_idx}/customer/tokens/validate/ | -   | {}   | 200    | -      |
      | checkout v1 countries    | anonymous  | GET    | api/checkout/v1/{channel_idx}/countries/                | -   | -    | 200    | -      |
      | checkout v1 countries    | customer   | GET    | api/checkout/v1/{channel_idx}/countries/                | -   | -    | 200    | -      |
      | checkout v1 countries    | bad-bearer | GET    | api/checkout/v1/{channel_idx}/countries/                | -   | -    | 200    | -      |
      | checkout payment webhook | anonymous  | POST   | api/checkout/v1/{channel_idx}/notify/payu/              | -   | {}   | 200    | -      |
      | checkout payment webhook | customer   | POST   | api/checkout/v1/{channel_idx}/notify/payu/              | -   | {}   | 200    | -      |
      | checkout payment webhook | bad-bearer | POST   | api/checkout/v1/{channel_idx}/notify/payu/              | -   | {}   | 200    | -      |

  Scenario Outline: PR-02 customer routes — <module> as <caller>
    Given the caller is <caller>
    And the caller presents the <key> key
    When the caller sends <method> to "<path>" with JSON <body>
    Then the answer is <status> with "-"
    And the answer does not contain "<absent>"

    Examples: customer routes
      | module           | caller     | method | path                                       | key | body | status | absent |
      | accounts         | anonymous  | GET    | api/accounts/v1/{channel_idx}/customer/me/ | -   | -    | 401    | -      |
      | accounts         | customer   | GET    | api/accounts/v1/{channel_idx}/customer/me/ | -   | -    | 401    | -      |
      | accounts         | bad-bearer | GET    | api/accounts/v1/{channel_idx}/customer/me/ | -   | -    | 401    | -      |
      | matrix v2 prices | anonymous  | GET    | api/matrix/v2/{channel_idx}/prices/        | -   | -    | 401    | -      |
      | matrix v2 prices | customer   | GET    | api/matrix/v2/{channel_idx}/prices/        | -   | -    | 200    | -      |
      | matrix v2 prices | bad-bearer | GET    | api/matrix/v2/{channel_idx}/prices/        | -   | -    | 401    | -      |
      | access me        | anonymous  | GET    | api/access/v2/me/                          | -   | -    | 401    | -      |
      | access me        | customer   | GET    | api/access/v2/me/                          | -   | -    | 200    | -      |
      | access me        | bad-bearer | GET    | api/access/v2/me/                          | -   | -    | 401    | -      |

  Scenario Outline: PR-03 key routes — <module> as <caller>
    Given the caller is <caller>
    And the caller presents the <key> key
    When the caller sends <method> to "<path>" with JSON <body>
    Then the answer is <status> with "-"
    And the answer does not contain "<absent>"

    Examples: key routes with the right key
      | module               | caller     | method | path                                                                       | key                   | body                                                                                  | status | absent          |
      | checkout cart        | anonymous  | POST   | api/checkout/v2/{channel_idx}/carts/                                       | checkout fixture      | {"items": [{"sku": "ENT-C003", "quantity": 1}], "currency_code": "EUR"}               | 201    | -               |
      | checkout cart        | customer   | POST   | api/checkout/v2/{channel_idx}/carts/                                       | checkout fixture      | {"items": [{"sku": "ENT-C003", "quantity": 1}], "currency_code": "EUR"}               | 201    | -               |
      | checkout cart        | bad-bearer | POST   | api/checkout/v2/{channel_idx}/carts/                                       | checkout fixture      | {"items": [{"sku": "ENT-C003", "quantity": 1}], "currency_code": "EUR"}               | 401    | -               |
      | contact form submit  | anonymous  | POST   | api/contact-forms/v2/{channel_idx}/submit/                                 | contact-forms fixture | {"email": "bdd-access-security@example.com", "body": {"name": "BDD access security"}} | 201    | -               |
      | contact form submit  | customer   | POST   | api/contact-forms/v2/{channel_idx}/submit/                                 | contact-forms fixture | {"email": "bdd-access-security@example.com", "body": {"name": "BDD access security"}} | 201    | -               |
      | contact form submit  | bad-bearer | POST   | api/contact-forms/v2/{channel_idx}/submit/                                 | contact-forms fixture | {"email": "bdd-access-security@example.com", "body": {"name": "BDD access security"}} | 201    | -               |
      | contact form types   | anonymous  | GET    | api/contact-forms/v2/{channel_idx}/form-types/                             | contact-forms fixture | -                                                                                     | 200    | -               |
      | contact form types   | customer   | GET    | api/contact-forms/v2/{channel_idx}/form-types/                             | contact-forms fixture | -                                                                                     | 200    | -               |
      | contact form types   | bad-bearer | GET    | api/contact-forms/v2/{channel_idx}/form-types/                             | contact-forms fixture | -                                                                                     | 200    | -               |
      | booking slots        | anonymous  | GET    | api/contact-forms/v2/{channel_idx}/bookings/slots/                         | contact_forms.booking | -                                                                                     | 400    | -               |
      | booking slots        | customer   | GET    | api/contact-forms/v2/{channel_idx}/bookings/slots/                         | contact_forms.booking | -                                                                                     | 400    | -               |
      | booking slots        | bad-bearer | GET    | api/contact-forms/v2/{channel_idx}/bookings/slots/                         | contact_forms.booking | -                                                                                     | 400    | -               |
      | agreements subscribe | anonymous  | POST   | api/agreements/v2/{channel_idx}/newsletter/subscribe/                      | agreements.subscribe  | {}                                                                                    | 400    | -               |
      | agreements subscribe | customer   | POST   | api/agreements/v2/{channel_idx}/newsletter/subscribe/                      | agreements.subscribe  | {}                                                                                    | 400    | -               |
      | agreements subscribe | bad-bearer | POST   | api/agreements/v2/{channel_idx}/newsletter/subscribe/                      | agreements.subscribe  | {}                                                                                    | 401    | -               |
      | reviews moderation   | anonymous  | PATCH  | api/reviews/v1/{channel_idx}/reviews/00000000-0000-4000-8000-000000000000/ | reviews.moderate      | {}                                                                                    | 404    | Invalid api key |
      | reviews moderation   | customer   | PATCH  | api/reviews/v1/{channel_idx}/reviews/00000000-0000-4000-8000-000000000000/ | reviews.moderate      | {}                                                                                    | 404    | Invalid api key |
      | reviews moderation   | bad-bearer | PATCH  | api/reviews/v1/{channel_idx}/reviews/00000000-0000-4000-8000-000000000000/ | reviews.moderate      | {}                                                                                    | 404    | Invalid api key |
      | returns              | anonymous  | GET    | api/returns/v1/{channel_idx}/returns/                                      | returns.api           | -                                                                                     | 401    | Invalid api key |
      | returns              | customer   | GET    | api/returns/v1/{channel_idx}/returns/                                      | returns.api           | -                                                                                     | 401    | Invalid api key |
      | returns              | bad-bearer | GET    | api/returns/v1/{channel_idx}/returns/                                      | returns.api           | -                                                                                     | 401    | Invalid api key |
      | vault                | anonymous  | GET    | api/vault/v1/{channel_idx}/payment_card/                                   | vault.api             | -                                                                                     | 401    | Invalid api key |
      | vault                | customer   | GET    | api/vault/v1/{channel_idx}/payment_card/                                   | vault.api             | -                                                                                     | 401    | Invalid api key |
      | vault                | bad-bearer | GET    | api/vault/v1/{channel_idx}/payment_card/                                   | vault.api             | -                                                                                     | 401    | Invalid api key |
