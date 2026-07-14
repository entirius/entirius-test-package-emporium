@suppliers @push-correctness
Feature: Mapping value modifiers — unit conversion
  As a platform operator
  I want to declare a one-shot unit conversion on a SupplierAttributeMapping
  (e.g. "this source field is grams, store it as kg") and have the push
  pipeline transform the value before writing to PIM
  So that scenarios like "Kestrel Supply ships weight_g=7800 → RealProduct.weight=7800
  kg" (a data-correctness regression) cannot happen again,
  and so that operator mistakes (e.g. picking grams_to_kg on a string field)
  produce a visible warning event instead of silently corrupting PIM.

  This slice adds two stable contract surfaces:
    1. SupplierAttributeMapping.modifier — request + response carries the new
       enum field (default "none"). Schema validation rejects unknown values.
    2. IntegrationEvent.event_type "mapping_transform_failed" — emitted when
       the transformer can't apply a modifier to the supplied value (type
       mismatch / invalid Decimal / unknown modifier). Severity = warning.
       The push pipeline never crashes on bad modifier config.

  Background:
    Given the test package has been imported
    And I am authenticated as an admin user

  @validate @schema-contract
  Scenario: Attribute mapping create rejects unknown modifier with 400
    # Contract-locking: anything outside enums.MappingValueModifier must be
    # rejected at the schema boundary. We don't have to provision a real
    # supplier/profile to exercise this — the request never reaches the service
    # layer because Pydantic Literal validation fires first.
    When I POST to the v2 admin endpoint "suppliers/admin/mapping-profiles/9999999/attribute-mappings/" with body
      """
      {
        "source_field": "weight_g",
        "target_type": "real_product",
        "target_identifier": "weight",
        "is_required": false,
        "modifier": "feet_to_meters"
      }
      """
    Then the response status should be 400

  @validate @v2-envelope
  Scenario: Attribute mapping create with valid modifier rejects unknown profile via v2 404
    # Once the schema accepts the modifier, the next layer (mapping_service)
    # still has to resolve the profile. Unknown profile → 404 + debug_id. This
    # locks the additive "modifier" field doesn't change the existing
    # not-found contract for the parent profile.
    When I POST to the v2 admin endpoint "suppliers/admin/mapping-profiles/9999999/attribute-mappings/" with body
      """
      {
        "source_field": "weight_g",
        "target_type": "real_product",
        "target_identifier": "weight",
        "is_required": false,
        "modifier": "grams_to_kg"
      }
      """
    Then the response status should be 404
    And the error response should have a debug_id
