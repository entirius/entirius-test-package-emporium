# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Step definitions for discount rule tests.

Implements cart operations, discount code application, and verification
of discount behavior for the Volkanos checkout API.
"""

from behave import given, then, when

from entirius_tests.csv_loader import (
    get_discount_rule_by_name,
    load_discount_rules,
)

# ─────────────────────────────────────────────────────────────────────────
# Given Steps - Cart Setup
# ─────────────────────────────────────────────────────────────────────────


def _cart_body(context, items, discounts=None):
    """Full v1 cart PUT body around the given items (schema rejects partial bodies)."""
    cart_data = getattr(context, "cart_data", None) or {}
    return {
        "cart": {
            "items": items,
            "discounts": discounts or [],
            "discount_amount": None,
            "base_total_price": None,
            "base_netto_price": None,
            "total_price": None,
            "validation_status": None,
        },
        "addresses": cart_data.get("addresses"),
        "payment_method": cart_data.get("payment_method"),
        "shipping_method": cart_data.get("shipping_method"),
        "language_code": cart_data.get("language_code", "en"),
        "currency_code": cart_data.get("currency_code", "EUR"),
        "country_code": cart_data.get("country_code", "PL"),
    }


@given("I have an empty cart")
def step_have_empty_cart(context):
    """Create a new empty cart or clear existing cart."""
    url = context.api.checkout_url(context.channel, "carts/")

    # Create cart with minimal data (empty cart)
    body = {
        "cart": {
            "items": [],
            "discounts": [],
            "discount_amount": None,
            "base_total_price": None,
            "base_netto_price": None,
            "total_price": None,
            "validation_status": None,
        },
        "addresses": None,
        "payment_method": None,
        "shipping_method": None,
        "language_code": "en",
        "currency_code": "EUR",
        "country_code": "PL",
    }

    context.response = context.api.post(url, json=body)

    if context.response.status_code in [200, 201]:
        response_json = context.response.json()
        # Checkout API returns: {"meta": {...}, "data": {"cart_id": "...", "cart": {...}, ...}}
        context.cart_data = response_json.get("data", {})
        context.cart_id = context.cart_data.get("cart_id")
    else:
        context.cart_id = None
        context.cart_data = None


@given('I add product "{sku}" with quantity {qty:d} to cart')
def step_add_product_to_cart(context, sku, qty):
    """Stage a product to be added when discount is applied."""
    if not hasattr(context, "cart_id") or context.cart_id is None:
        raise ValueError("Cart not created. Use 'Given I have an empty cart' first")

    # Store items to be sent with the discount apply step
    if not hasattr(context, "pending_items"):
        context.pending_items = []
    context.pending_items.append({"sku": sku, "quantity": qty, "offer_price": None, "extra": None})


@given("I add products totaling at least {amount:d} PLN")
def step_add_products_totaling(context, amount):
    """Add sufficient products to reach minimum cart value (in EUR despite name PLN).

    The runtime cart price is the only source of truth (pricelists/tax/special prices
    shift with the dataset), so probe with 1 unit and derive the needed quantity."""
    if not hasattr(context, "cart_id") or context.cart_id is None:
        raise ValueError("Cart not created. Use 'Given I have an empty cart' first")

    probe_body = _cart_body(context, items=[{"sku": "ENT-C001", "quantity": 1, "offer_price": None, "extra": None}])
    url = context.api.checkout_url(context.channel, f"carts/{context.cart_id}/")
    response = context.api.put(url, json=probe_body)
    items = response.json().get("data", {}).get("cart", {}).get("items", [])
    unit_price = float(items[0]["base_unit_price"]) if items else 0.0
    if unit_price <= 0:
        raise AssertionError(f"Probe item has no price (items={items}) — stock/price pipeline not settled?")
    quantity_needed = max(1, -(-amount // int(unit_price)))  # ceil division

    if not hasattr(context, "pending_items"):
        context.pending_items = []
    context.pending_items.append({"sku": "ENT-C001", "quantity": quantity_needed, "offer_price": None, "extra": None})


@given("I add products totaling {amount:d} PLN")
def step_add_products_exact_total(context, amount):
    """Add products to reach exact cart value (for testing thresholds)."""
    # For exact total, use the same logic as "at least" - getting exact is difficult without prices
    step_add_products_totaling(context, amount)


# ─────────────────────────────────────────────────────────────────────────
# Given Steps - Authentication
# ─────────────────────────────────────────────────────────────────────────


@given("I am authenticated as a new user with no orders")
def step_authenticated_new_user(context):
    """Authenticate as a user with no order history."""
    # TODO: Create test user, authenticate, verify no orders
    raise NotImplementedError("New user authentication not yet implemented")


@given("I am not authenticated")
def step_not_authenticated(context):
    """Ensure no authentication token is set."""
    context.api.clear_auth_token()


@given("I am authenticated as a user with existing orders")
def step_authenticated_existing_user(context):
    """Authenticate as a user with order history."""
    # TODO: Create test user, create past order, authenticate
    raise NotImplementedError("Existing user authentication not yet implemented")


# ─────────────────────────────────────────────────────────────────────────
# When Steps - CSV Loading
# ─────────────────────────────────────────────────────────────────────────


@when("the CSV discount rules are loaded")
def step_load_csv_discount_rules(context):
    """Load discount rules from CSV for verification."""
    context.csv_discount_rules = load_discount_rules(context.test_package_path)


# ─────────────────────────────────────────────────────────────────────────
# When Steps - Discount Application
# ─────────────────────────────────────────────────────────────────────────


@when('I apply discount code "{code}"')
def step_apply_discount_code(context, code):
    """Apply a discount code to the cart."""
    if not hasattr(context, "cart_id") or context.cart_id is None:
        raise ValueError("Cart not created. Use 'Given I have an empty cart' first")

    context.discount_code = code

    # Use pending items if available, otherwise fetch from cart
    items = getattr(context, "pending_items", None) or []
    if not items and hasattr(context, "cart_data") and context.cart_data:
        cart_section = context.cart_data.get("cart", {})
        raw_items = cart_section.get("items", [])
        items = [
            {"sku": i["sku"], "quantity": i["quantity"], "offer_price": i.get("offer_price"), "extra": i.get("extra")}
            for i in raw_items
        ]

    # Apply discount code with items in a single PUT
    url = context.api.checkout_url(context.channel, f"carts/{context.cart_id}/")

    body = {
        "cart": {
            "items": items,
            "discounts": [{"code": code, "sku": None, "quantity": None, "clear_discounts": False}],
            "discount_amount": None,
            "base_total_price": None,
            "base_netto_price": None,
            "total_price": None,
            "validation_status": None,
        },
        "addresses": context.cart_data.get("addresses"),
        "payment_method": context.cart_data.get("payment_method"),
        "shipping_method": context.cart_data.get("shipping_method"),
        "language_code": context.cart_data.get("language_code", "en"),
        "currency_code": context.cart_data.get("currency_code", "EUR"),
        "country_code": context.cart_data.get("country_code", "PL"),
    }

    context.response = context.api.put(url, json=body)

    # Clear pending items after use
    context.pending_items = []

    if context.response.status_code == 200:
        response_json = context.response.json()
        context.cart_data = response_json.get("data", {})
    else:
        # Keep response for error checking
        pass


@when("I apply an expired discount code")
def step_apply_expired_code(context):
    """Attempt to apply an expired discount code."""
    # TODO: Create or use expired discount code, attempt to apply
    raise NotImplementedError("Expired code test not yet implemented")


@when("I remove the discount code")
def step_remove_discount_code(context):
    """Remove applied discount from cart."""
    if not hasattr(context, "cart_id") or context.cart_id is None:
        raise ValueError("Cart not created. Use 'Given I have an empty cart' first")

    # Get current cart data
    url = context.api.checkout_url(context.channel, f"carts/{context.cart_id}/")
    resp = context.api.get(url)
    if resp.status_code == 200:
        resp_json = resp.json()
        context.cart_data = resp_json.get("data", {})
    else:
        context.cart_data = {}

    # Extract current cart structure
    cart_section = context.cart_data.get("cart", {})
    items = cart_section.get("items", [])

    # Update cart with clear_discounts flag
    body = {
        "cart": {
            "items": items,
            "discounts": [{"code": None, "sku": None, "quantity": None, "clear_discounts": True}],
            "discount_amount": None,
            "base_total_price": None,
            "base_netto_price": None,
            "total_price": None,
            "validation_status": None,
        },
        "addresses": context.cart_data.get("addresses"),
        "payment_method": context.cart_data.get("payment_method"),
        "shipping_method": context.cart_data.get("shipping_method"),
        "language_code": context.cart_data.get("language_code", "en"),
        "currency_code": context.cart_data.get("currency_code", "EUR"),
        "country_code": context.cart_data.get("country_code", "PL"),
    }

    context.response = context.api.put(url, json=body)

    if context.response.status_code == 200:
        response_json = context.response.json()
        context.cart_data = response_json.get("data", {})


@when("I calculate cart totals")
def step_calculate_cart_totals(context):
    """Recalculate cart totals (triggers automatic discounts)."""
    if not hasattr(context, "cart_id") or context.cart_id is None:
        raise ValueError("Cart not created. Use 'Given I have an empty cart' first")

    # GET cart details to trigger automatic discount evaluation
    url = context.api.checkout_url(context.channel, f"carts/{context.cart_id}/")
    context.response = context.api.get(url)

    if context.response.status_code == 200:
        response_json = context.response.json()
        context.cart_data = response_json.get("data", {})


# ─────────────────────────────────────────────────────────────────────────
# Then Steps - CSV Verification
# ─────────────────────────────────────────────────────────────────────────


@then("the discount rules count should be {count:d}")
def step_verify_discount_rules_count(context, count):
    """Verify number of discount rules in CSV."""
    actual_count = len(context.csv_discount_rules)
    assert actual_count == count, f"Expected {count} discount rules in CSV, found {actual_count}"


@then('the discount rules should contain rule with name "{name}"')
def step_verify_discount_rule_exists(context, name):
    """Verify a specific discount rule exists in CSV."""
    rule = get_discount_rule_by_name(context.test_package_path, name)
    assert rule is not None, f"Discount rule '{name}' not found in CSV"


# ─────────────────────────────────────────────────────────────────────────
# Then Steps - Discount Success
# ─────────────────────────────────────────────────────────────────────────


@then("the discount should be applied successfully")
def step_discount_applied_success(context):
    """Verify discount was applied to cart."""
    assert context.response.status_code == 200, (
        f"Expected status 200, got {context.response.status_code}: {context.response.text[:200]}"
    )

    # Verify discount is present in cart data
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    assert len(discounts) > 0, "No discounts found in cart"

    # Verify status is OK (no errors in messages)
    response_json = context.response.json()
    meta = response_json.get("meta", {})
    status = meta.get("status", "OK")
    errors = meta.get("errors", [])

    assert status in ["OK", "CREATED"] or not errors, f"Discount application failed with errors: {errors}"


@then("the discount should not be applied")
def step_discount_not_applied(context):
    """Verify discount was rejected."""
    # Check for error status or error messages
    response_json = context.response.json()
    meta = response_json.get("meta", {})
    status = meta.get("status", "OK")
    errors = meta.get("errors", [])
    messages = meta.get("messages", [])

    # Discount rejection can be indicated by FAIL status or errors/messages
    assert status == "FAIL" or len(errors) > 0 or len(messages) > 0, (
        "Expected discount to be rejected, but no errors found"
    )


# ─────────────────────────────────────────────────────────────────────────
# Then Steps - Discount Details
# ─────────────────────────────────────────────────────────────────────────


@then('the discount type should be "{discount_type}"')
def step_verify_discount_type(context, discount_type):
    """Verify discount modifier type."""
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    assert len(discounts) > 0, "No discounts found in cart"

    # Check first discount's modifier
    discount = discounts[0]
    actual_modifier = discount.get("modifier")

    assert actual_modifier == discount_type, f"Expected discount modifier '{discount_type}', got '{actual_modifier}'"


@then("the discount value should be {value:d} percent")
def step_verify_discount_percent(context, value):
    """Verify percentage discount value."""
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    assert len(discounts) > 0, "No discounts found in cart"

    discount = discounts[0]
    extra_value = discount.get("extra_value")

    # For progressive/step discounts, extra_value is a dict with thresholds
    # We need to calculate actual percent from discount_amount and base_total_price
    if isinstance(extra_value, dict) and "EUR" in extra_value and isinstance(extra_value["EUR"], dict):
        # Progressive discount - calculate actual percent applied
        base_total = float(cart_section.get("base_total_price", 0))
        discount_amount = float(cart_section.get("discount_amount", 0))

        if base_total > 0:
            actual_value = round((discount_amount / base_total) * 100)
        else:
            actual_value = 0
    elif isinstance(extra_value, dict):
        # Multi-currency simple discount
        actual_value = extra_value.get("EUR", extra_value.get("PLN", 0))
    else:
        # Simple int value
        actual_value = extra_value

    assert actual_value == value, f"Expected discount value {value}%, got {actual_value}%"


@then("the discount amount should be {amount:d} EUR")
def step_verify_discount_amount(context, amount):
    """Verify fixed discount amount."""
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    assert len(discounts) > 0, "No discounts found in cart"

    discount = discounts[0]
    extra_value = discount.get("extra_value")

    # extra_value can be int or dict with currency keys
    if isinstance(extra_value, dict):
        actual_value = extra_value.get("EUR", extra_value.get("PLN", 0))
    else:
        actual_value = extra_value

    assert actual_value == amount, f"Expected discount amount {amount} EUR, got {actual_value}"


# ─────────────────────────────────────────────────────────────────────────
# Then Steps - Gratis Products
# ─────────────────────────────────────────────────────────────────────────


@then("gratis products should be available")
def step_verify_gratis_available(context):
    """Verify gratis products are offered."""
    cart_section = context.cart_data.get("cart", {})
    is_gratis_available = cart_section.get("is_gratis_available", False)

    assert is_gratis_available, "Expected gratis products to be available"


@then("{count:d} gratis products should be available")
def step_verify_gratis_count(context, count):
    """Verify exact number of gratis products available for GRATIS_STEP rule."""
    cart_section = context.cart_data.get("cart", {})
    gratis_rules = cart_section.get("gratis_rules") or []

    # Find GRATIS_STEP rule (or rule matching last applied discount code)
    gratis_step_rules = [r for r in gratis_rules if "STEP" in str(r.get("code", ""))]

    if gratis_step_rules:
        # Get max_available_quantity from GRATIS_STEP rule
        actual_count = gratis_step_rules[0].get("max_available_quantity", 0)
        assert actual_count == count, f"Expected {count} gratis products available for GRATIS_STEP, got {actual_count}"
    else:
        assert False, f"Expected GRATIS_STEP rule with {count} gratis products, but not found in gratis_rules"


# ─────────────────────────────────────────────────────────────────────────
# Then Steps - Free Shipping
# ─────────────────────────────────────────────────────────────────────────


@then("free shipping should be enabled")
def step_verify_free_shipping(context):
    """Verify free shipping is applied."""
    free_shipping = context.cart_data.get("free_shipping", False)

    assert free_shipping, "Expected free shipping to be enabled"


# ─────────────────────────────────────────────────────────────────────────
# Then Steps - Automatic Discounts
# ─────────────────────────────────────────────────────────────────────────


@then("an automatic discount should be applied")
def step_verify_auto_discount_applied(context):
    """Verify automatic discount was triggered."""
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    # Find automatic discount (automatic_applications=true)
    auto_discounts = [d for d in discounts if d.get("automatic_applications", False)]

    assert len(auto_discounts) > 0, f"Expected automatic discount to be applied, but found none. Discounts: {discounts}"


@then("no automatic discount should be applied")
def step_verify_no_auto_discount(context):
    """Verify no automatic discount was triggered."""
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    # Find automatic discount (automatic_applications=true)
    auto_discounts = [d for d in discounts if d.get("automatic_applications", False)]

    assert len(auto_discounts) == 0, f"Expected no automatic discount, but found {len(auto_discounts)}"


# ─────────────────────────────────────────────────────────────────────────
# Then Steps - Combinable Discounts
# ─────────────────────────────────────────────────────────────────────────


@then("the automatic discount should also be applied")
def step_verify_auto_discount_also_applied(context):
    """Verify automatic discount is present alongside manual discount."""
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    # Find automatic discount
    auto_discounts = [d for d in discounts if d.get("automatic_applications", False)]
    # Find code-based discount
    code_discounts = [d for d in discounts if d.get("code") and not d.get("automatic_applications", False)]

    assert len(auto_discounts) > 0, "Expected automatic discount to be applied"
    assert len(code_discounts) > 0, "Expected code-based discount to be applied"


@then("both discounts should be active")
def step_verify_both_discounts_active(context):
    """Verify multiple discounts are active."""
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    # Check for valid/active discounts (status='valid' or no status field)
    active_discounts = [d for d in discounts if d.get("status") != "invalid"]

    assert len(active_discounts) >= 2, f"Expected at least 2 active discounts, found {len(active_discounts)}"


@then("only one discount should be active")
def step_verify_only_one_discount(context):
    """Verify only one discount is active (non-combinable)."""
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    # Check for valid/active discounts
    active_discounts = [d for d in discounts if d.get("status") != "invalid"]

    assert len(active_discounts) == 1, f"Expected exactly 1 active discount, found {len(active_discounts)}"


# ─────────────────────────────────────────────────────────────────────────
# Then Steps - No Discount
# ─────────────────────────────────────────────────────────────────────────


@then("no discount should be active")
def step_verify_no_discount(context):
    """Verify no discounts are applied to cart."""
    cart_section = context.cart_data.get("cart", {})
    discounts = cart_section.get("discounts", [])

    # Check for valid/active discounts
    active_discounts = [d for d in discounts if d.get("status") != "invalid"]

    assert len(active_discounts) == 0, (
        f"Expected no active discounts, found {len(active_discounts)}: {active_discounts}"
    )


@then("the cart total should reflect full price")
def step_verify_full_price(context):
    """Verify cart total is undiscounted."""
    cart_section = context.cart_data.get("cart", {})
    discount_amount = cart_section.get("discount_amount", 0) or 0

    # Discount amount should be 0 or None for full price
    assert float(discount_amount) == 0, f"Expected no discount (0 PLN), but found discount_amount={discount_amount}"


# ─────────────────────────────────────────────────────────────────────────
# Then Steps - Error Messages
# ─────────────────────────────────────────────────────────────────────────


@then("the error message should indicate minimum order amount not met")
def step_verify_min_order_error(context):
    """Verify error indicates minimum order requirement."""
    response_json = context.response.json()
    meta = response_json.get("meta", {})
    errors = meta.get("errors", [])
    messages = meta.get("messages", [])

    # Combine errors and messages for checking
    all_messages = str(errors) + str(messages)

    # Check for keywords related to minimum order amount
    keywords = ["min", "minimum", "order", "amount", "required"]
    found = any(keyword.lower() in all_messages.lower() for keyword in keywords)

    assert found, f"Expected error about minimum order amount, got: {all_messages}"


@then("the error message should indicate user must be logged in")
def step_verify_login_required_error(context):
    """Verify error indicates authentication required."""
    response_json = context.response.json()
    meta = response_json.get("meta", {})
    errors = meta.get("errors", [])
    messages = meta.get("messages", [])

    all_messages = str(errors) + str(messages)

    keywords = ["login", "log in", "authenticate", "authentication", "logged in", "user"]
    found = any(keyword.lower() in all_messages.lower() for keyword in keywords)

    assert found, f"Expected error about login required, got: {all_messages}"


@then("the error message should indicate not eligible")
def step_verify_not_eligible_error(context):
    """Verify error indicates user not eligible for discount."""
    response_json = context.response.json()
    meta = response_json.get("meta", {})
    errors = meta.get("errors", [])
    messages = meta.get("messages", [])

    all_messages = str(errors) + str(messages)

    keywords = ["eligible", "eligibility", "not allowed", "cannot use", "restricted"]
    found = any(keyword.lower() in all_messages.lower() for keyword in keywords)

    assert found, f"Expected error about eligibility, got: {all_messages}"


@then("the error message should indicate discounts cannot be combined")
def step_verify_cannot_combine_error(context):
    """Verify error indicates discounts are not combinable."""
    response_json = context.response.json()
    meta = response_json.get("meta", {})
    errors = meta.get("errors", [])
    messages = meta.get("messages", [])

    all_messages = str(errors) + str(messages)

    keywords = ["combine", "combinable", "stack", "multiple", "already applied"]
    found = any(keyword.lower() in all_messages.lower() for keyword in keywords)

    assert found, f"Expected error about combining discounts, got: {all_messages}"


@then("the error message should indicate code not found")
def step_verify_code_not_found_error(context):
    """Verify error indicates invalid discount code."""
    response_json = context.response.json()
    meta = response_json.get("meta", {})
    errors = meta.get("errors", [])
    messages = meta.get("messages", [])

    all_messages = str(errors) + str(messages)

    keywords = ["not found", "invalid", "code", "discount"]
    found = any(keyword.lower() in all_messages.lower() for keyword in keywords)

    assert found, f"Expected error about invalid code, got: {all_messages}"


@then("the error message should indicate code expired")
def step_verify_code_expired_error(context):
    """Verify error indicates discount code has expired."""
    response_json = context.response.json()
    meta = response_json.get("meta", {})
    errors = meta.get("errors", [])
    messages = meta.get("messages", [])

    all_messages = str(errors) + str(messages)

    keywords = ["expired", "expir", "no longer valid", "ended"]
    found = any(keyword.lower() in all_messages.lower() for keyword in keywords)

    assert found, f"Expected error about expired code, got: {all_messages}"


@then("the error message should indicate cart is empty")
def step_verify_cart_empty_error(context):
    """Verify error indicates cart has no items."""
    response_json = context.response.json()
    meta = response_json.get("meta", {})
    errors = meta.get("errors", [])
    messages = meta.get("messages", [])

    all_messages = str(errors) + str(messages)

    keywords = ["empty", "cart", "no items"]
    found = any(keyword.lower() in all_messages.lower() for keyword in keywords)

    assert found, f"Expected error about empty cart, got: {all_messages}"
