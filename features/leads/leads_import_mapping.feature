@leads @v2 @admin @import-mapping
Feature: Leads — import of a file with its own column names (U17)
  As a sales operator
  I want a spreadsheet whose columns are named the way people name them to land in the right CRM fields
  So that a typical Excel base imports without renaming its columns first

  Not one-shot: the import is idempotent (a re-run matches instead of creating). Data:
  package/leads--human-headers-pl.csv (cp1250, `;`, Polish headers, 2 rows) and package/leads--human-headers.xlsx
  (first sheet "Klienci", 2 rows). Uploads go through `test/import-now/` (imports in the service process), the
  proposal through `imports/preview/`, which stores nothing. An import always carries a confirmed mapping (a JSON
  object): `auto` is refused, so IM-2 and IM-4 send the preview's proposal back, the way the CMS does.

  Background:
    Given the channel is the primary channel
    And I am authenticated as an admin user

  Scenario: IM-1 the preview proposes a field for every Polish header
    When I upload the package file "leads--human-headers-pl.csv" to the v2 admin endpoint "leads/admin/{channel_idx}/imports/preview/"
    Then the response status should be 200
    And the response field "encoding" should equal "cp1250"
    And the response field "delimiter" should equal ";"
    And the response field "row_count" should equal integer 2
    And the import column "Nazwa firmy" should go to "company_name"
    And the import column "Strona WWW" should go to "website"
    And the import column "Adres e-mail" should go to "email"
    And the import column "Imię i nazwisko" should go to "full_name"
    And the import column "Stanowisko" should go to "job_title"
    And the import column "Telefon" should go to "phone"
    And the import column "Uwagi" should go to "description"
    And the import column "NIP" should be ignored as "no_crm_field" or go to a custom field

  Scenario: IM-2 a cp1250 CSV with Polish headers imports companies and contacts into the right fields
    When I upload the package file "leads--human-headers-pl.csv" to the v2 admin endpoint "leads/admin/{channel_idx}/imports/preview/"
    Then the response status should be 200
    When I import the package file "leads--human-headers-pl.csv" with the proposed mapping through "leads/admin/{channel_idx}/test/import-now/"
    Then the response status should be 200
    And the response field "status" should equal "done"
    And the import counts created plus matched should equal 2
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=import-mapping-lodz.test"
    Then the response field "count" should equal integer 1
    And the first result field "name" equals "Łódzka Spółka Ogrodnicza"
    And I save the first result field "id" as "company_id"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/contacts/?company={company_id}"
    Then the results should contain an item with "email" equal to "jan.zolc@import-mapping-lodz.test"
    And the results should contain an item with "first_name" equal to "Jan"
    And the results should contain an item with "last_name" equal to "Żółć"
    And the results should contain an item with "job_title" equal to "Prezes zarządu"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=import-mapping-gdansk.test"
    Then the first result field "name" equals "Gdańskie Żagle"
    And I save the first result field "id" as "gdansk_id"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/contacts/?company={gdansk_id}"
    Then the results should contain an item with "first_name" equal to "Anna"
    And the results should contain an item with "last_name" equal to "Kowalska"

  Scenario: IM-3 an xlsx file imports with the mapping the user confirmed
    When I upload the package file "leads--human-headers.xlsx" to the v2 admin endpoint "leads/admin/{channel_idx}/imports/preview/"
    Then the response status should be 200
    And the response field "format" should equal "xlsx"
    And the response field "sheet" should equal "Klienci"
    And the import column "Firma" should go to "company_name"
    And the import column "Tel." should go to "phone"
    When I import the package file "leads--human-headers.xlsx" with the mapping "{"Firma": "company_name", "E-mail": "email", "Tel.": "phone", "Imię": "first_name", "Nazwisko": "last_name", "Branża": "ignore"}" through "leads/admin/{channel_idx}/test/import-now/"
    Then the response status should be 200
    And the response field "status" should equal "done"
    And the import counts created plus matched should equal 2
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=import-mapping-krakow.test"
    Then the first result field "name" equals "Krakowskie Meble"
    And I save the first result field "id" as "company_id"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/contacts/?company={company_id}"
    Then the results should contain an item with "first_name" equal to "Ewa"
    And the results should contain an item with "phone" equal to "48600300400"

  Scenario: IM-4 a file named name,domain,email gets its company names (C9)
    When I upload the package file "leads--c9-name-domain.csv" to the v2 admin endpoint "leads/admin/{channel_idx}/imports/preview/"
    Then the response status should be 200
    And the import column "name" should go to "company_name"
    When I import the package file "leads--c9-name-domain.csv" with the proposed mapping through "leads/admin/{channel_idx}/test/import-now/"
    Then the response status should be 200
    And the response field "status" should equal "done"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/companies/?search=c9-import-alfa.test"
    Then the first result field "name" equals "Test Import Alfa"

  Scenario: IM-5 a mapping with an unknown field is refused and imports nothing
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/imports/"
    Then I save the response field "count" as "imports_before"
    When I import the package file "leads--human-headers-pl.csv" with the mapping "{"Nazwa firmy": "fax"}" through "leads/admin/{channel_idx}/imports/"
    Then the response status should be 400
    And the answer names the issue "UNKNOWN_FIELD"
    When I GET the v2 admin endpoint "leads/admin/{channel_idx}/imports/"
    Then the response count should equal the saved "imports_before"

  Scenario: IM-6 a full name together with a first name is refused
    When I import the package file "leads--human-headers-pl.csv" with the mapping "{"Strona WWW": "website", "Imię i nazwisko": "full_name", "Stanowisko": "first_name"}" through "leads/admin/{channel_idx}/imports/"
    Then the response status should be 400
    And the answer names the issue "DUPLICATE_FIELD"

  Scenario Outline: IM-7 the mapping "auto" is refused: <endpoint>
    When I import the package file "leads--c9-name-domain.csv" with the mapping "auto" through "leads/admin/{channel_idx}/<endpoint>"
    Then the response status should be 400
    And the answer names the issue "INVALID_JSON"

    Examples:
      | endpoint         |
      | imports/         |
      | test/import-now/ |
      | imports/preview/ |
