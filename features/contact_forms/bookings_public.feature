@spec-first @contact-forms @bookings @public @v2
Feature: Contact Forms — Public Booking API (v2.1.0)
  As a website visitor
  I want to see available booking slots and book one
  So that I can schedule a consultation

  Background:
    Given the test package has been imported
    And the channel is the primary channel
    And the global ContactFormsSettings has bookings_enabled=true
    And the channel has a BookingConfig with enabled=true

  Scenario: List slots requires API key
    When I GET the v2 endpoint "contact-forms/{channel_idx}/bookings/slots/" without X-API-KEY
    Then the response status should be 401

  Scenario: List slots returns the configured grid
    When I GET the v2 endpoint "contact-forms/{channel_idx}/bookings/slots/?days=2" with a booking-scoped X-API-KEY
    Then the response status should be 200
    And the response should contain key "timezone"
    And the response should contain key "slot_duration_minutes"
    And the response should contain key "days"

  Scenario: A contact-form-scoped key cannot book
    When I POST the v2 endpoint "contact-forms/{channel_idx}/bookings/" with a contact-form-scoped X-API-KEY and a valid booking payload
    Then the response status should be 401

  Scenario: Booking creation returns 201 with event id and lead id
    When I POST the v2 endpoint "contact-forms/{channel_idx}/bookings/" with a booking-scoped X-API-KEY and a valid booking payload
    Then the response status should be 201
    And the response should contain key "event_id"
    And the response should contain key "meet_link"
    And the response should contain key "lead_id"
    And the response should contain key "contact_form_id"

  Scenario: Booking with global toggle off returns 400
    Given the global ContactFormsSettings has bookings_enabled=false
    When I POST the v2 endpoint "contact-forms/{channel_idx}/bookings/" with a booking-scoped X-API-KEY and a valid booking payload
    Then the response status should be 400
