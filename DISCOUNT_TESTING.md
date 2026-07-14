# Discount Rules Testing Guide

Comprehensive guide for testing discount rules in the Volkanos checkout system.

## Quick Start

```bash
# From entirius-docker root

# Import test package (includes discount fixtures)
./repos/entirius-test-package/scripts/entirius-docker-seed.sh

# Run all discount rule tests
make test-tags TAGS=@discount-rules

# Run specific subset
make test-tags TAGS="@discount-rules and @gratis"
```

## Test Architecture

### Two-Repository Pattern

Discount rule testing follows the standard Entirius test architecture:

1. **entirius-test-package** -- Test data (fixtures + CSV)
   - `fixtures/django_checkout.discounts.yaml` -- Django fixture with 10 discount rules
   - `package/discount-rules.csv` -- Metadata for BDD test verification

2. **entirius-tests** -- BDD scenarios (Behave)
   - `features/checkout/discount_rules.feature` -- 30+ test scenarios
   - `features/checkout/steps/discount_steps.py` -- Step definitions
   - `src/entirius_tests/csv_loader.py` -- CSV helpers (`load_discount_rules`, `get_discount_rule_by_code`)

### Data Flow

```
Fixture (YAML)
    ↓ loaddata
  Database (DiscountRuleCode, DiscountCode)
    ↓ API
  Cart applies discount
    ↓ Behave test
  Verify behavior ← CSV metadata
```

## Test Coverage

### 10 Discount Rules

| Rule Name | Code | Modifier | Coverage |
|-----------|------|----------|----------|
| TEST_PERCENT_10 | PERCENT10 | percent_discount | Simple percent |
| TEST_PRICE_50 | PRICE50 | price_discount | Fixed amount + minimum |
| TEST_CHEAPEST_GRATIS | CHEAPEST_FREE | cheapest_gratis | Gratis products |
| TEST_MOST_EXPENSIVE_GRATIS | EXPENSIVE_FREE | most_expensive_gratis | Gratis products |
| TEST_FREE_SHIPPING | FREESHIP | free_shipping | Shipping rules |
| TEST_STEP_PRICE_PERCENT | STEP_PRICE_PCT | step_price_percent_discount | Progressive % |
| TEST_GRATIS_STEPPED | GRATIS_STEP | gratis_stepped | Progressive gratis |
| TEST_AUTO_APPLY | AUTO | percent_discount (auto) | Automatic application |
| TEST_FIRST_ORDER_LOGGED | FIRST_LOGGED | percent_discount (target) | User targeting |
| TEST_COMBINABLE | COMBINE50 | price_discount (combinable) | Stackable discounts |

### 35+ Test Scenarios

**Import Verification** (1 scenario)
- CSV structure and rule existence

**Simple Discounts** (4 scenarios)
- Percent discount (10%)
- Fixed price discount (50 PLN)
- Minimum order amount enforcement

**Gratis Products** (4 scenarios)
- Cheapest product free
- Most expensive product free
- Minimum order enforcement

**Free Shipping** (2 scenarios)
- Apply at minimum
- Reject below minimum

**Progressive Discounts** (7 scenarios)
- Step price percent at 200/500/1000/2000 PLN
- Gratis stepped at 300/600/1000 PLN

**Automatic Application** (2 scenarios)
- Auto-apply at threshold
- No auto-apply below threshold

**User Targeting** (3 scenarios)
- First order logged users (success)
- First order guest users (rejected)
- First order existing users (rejected)

**Combinable Discounts** (3 scenarios)
- Apply combinable alone
- Stack with automatic discount
- Non-combinable rejection

**Edge Cases** (7 scenarios)
- Invalid code
- Expired code
- Remove discount
- Empty cart
- Various error messages

## Test Tags

Use tags to run specific test subsets:

| Tag | Scope |
|-----|-------|
| `@discount-rules` | All discount tests (35+ scenarios) |
| `@import-verification` | CSV structure verification (1 scenario) |
| `@checkout` | All checkout tests (includes discounts) |
| `@auth` | Tests requiring authentication (3 scenarios) |

### Examples

```bash
# All discount tests
make test-tags TAGS=@discount-rules

# Import verification only
make test-tags TAGS="@discount-rules and @import-verification"

# Authenticated discount tests
make test-tags TAGS="@discount-rules and @auth"

# Exclude auth tests
make test-tags TAGS="@discount-rules and not @auth"
```

## Step Definitions

### Cart Management

```gherkin
Given I have an empty cart
Given I add product "ENT-S001" with quantity 1 to cart
Given I add products totaling at least 200 PLN
Given I add products totaling 900 PLN
```

### Authentication

```gherkin
Given I am authenticated as a new user with no orders
Given I am not authenticated
Given I am authenticated as a user with existing orders
```

### CSV Loading

```gherkin
When the CSV discount rules are loaded
```

### Discount Application

```gherkin
When I apply discount code "PERCENT10"
When I apply an expired discount code
When I remove the discount code
When I calculate cart totals
```

### Verification - Success

```gherkin
Then the discount should be applied successfully
Then the discount should not be applied
Then the discount type should be "percent_discount"
Then the discount value should be 10 percent
Then the discount amount should be 50 PLN
```

### Verification - Gratis

```gherkin
Then gratis products should be available
Then 2 gratis products should be available
```

### Verification - Shipping

```gherkin
Then free shipping should be enabled
```

### Verification - Automatic

```gherkin
Then an automatic discount should be applied
Then no automatic discount should be applied
```

### Verification - Combinable

```gherkin
Then the automatic discount should also be applied
Then both discounts should be active
Then only one discount should be active
```

### Verification - No Discount

```gherkin
Then no discount should be active
Then the cart total should reflect full price
```

### Verification - Errors

```gherkin
Then the error message should indicate minimum order amount not met
Then the error message should indicate user must be logged in
Then the error message should indicate not eligible
Then the error message should indicate discounts cannot be combined
Then the error message should indicate code not found
Then the error message should indicate code expired
Then the error message should indicate cart is empty
```

## Implementation Status

### ✅ Complete

- [x] Fixture structure (YAML)
- [x] CSV metadata file
- [x] CSV loader functions
- [x] BDD feature file (35 scenarios)
- [x] Step definition stubs
- [x] Import script integration
- [x] Documentation

### 🚧 TODO (Step Implementation Required)

All step definitions are **stubs** with `NotImplementedError`. Implementation requires:

1. **Checkout API client integration**
   - Cart creation: `POST /api/v1/checkout/{channel}/cart/`
   - Add to cart: `POST /api/v1/checkout/{channel}/cart/{cart_id}/items/`
   - Apply discount: `POST /api/v1/checkout/{channel}/cart/{cart_id}/discount/`
   - Remove discount: `DELETE /api/v1/checkout/{channel}/cart/{cart_id}/discount/`
   - Get cart: `GET /api/v1/checkout/{channel}/cart/{cart_id}/`

2. **Cart state management**
   - Store `cart_id` in `context`
   - Calculate cart totals
   - Track applied discounts

3. **Product price queries**
   - Query prices via Matrix/PriceManager
   - Build cart to reach target amounts

4. **User management**
   - Create test users
   - Authenticate users
   - Create order history

5. **Response validation**
   - Extract discount details from cart response
   - Verify discount calculations
   - Parse error messages

### Recommendation: Incremental Implementation

Implement in order:

1. **Phase 1: Basic cart + simple discount** (2-3 scenarios)
   - Empty cart
   - Add product
   - Apply PERCENT10
   - Verify discount applied

2. **Phase 2: Minimum order enforcement** (2-3 scenarios)
   - Add products to total
   - Apply PRICE50 (success and failure)

3. **Phase 3: Gratis products** (2-3 scenarios)
   - CHEAPEST_FREE
   - Verify gratis available

4. **Phase 4: Progressive discounts** (4 scenarios)
   - STEP_PRICE_PCT at various thresholds

5. **Phase 5: Advanced features** (remaining scenarios)
   - Automatic application
   - Combinable discounts
   - User targeting
   - Edge cases

## CSV-Driven Testing

All expected values come from `discount-rules.csv`, not hardcoded in tests.

### Example: Verify Rule Exists

```python
# In step definition
package_path = context.config.userdata.get("test_package_path")
rule = get_discount_rule_by_code(package_path, "PERCENT10")
assert rule is not None, "PERCENT10 not found"
assert rule["modifier"] == "percent_discount"
assert rule["extra_value"] == "10"
```

### Example: Verify All Rules Imported

```python
rules = load_discount_rules(package_path)
assert len(rules) == 10, f"Expected 10 rules, found {len(rules)}"
```

## API Endpoint Patterns (TBD)

**Note:** Exact endpoints depend on Volkanos Checkout API design. Expected patterns:

### Cart Operations

```http
POST /api/v1/checkout/{channel}/cart/
GET /api/v1/checkout/{channel}/cart/{cart_id}/
DELETE /api/v1/checkout/{channel}/cart/{cart_id}/
```

### Cart Items

```http
POST /api/v1/checkout/{channel}/cart/{cart_id}/items/
PATCH /api/v1/checkout/{channel}/cart/{cart_id}/items/{item_id}/
DELETE /api/v1/checkout/{channel}/cart/{cart_id}/items/{item_id}/
```

### Discount Codes

```http
POST /api/v1/checkout/{channel}/cart/{cart_id}/discount/
DELETE /api/v1/checkout/{channel}/cart/{cart_id}/discount/
GET /api/v1/checkout/{channel}/cart/{cart_id}/available-discounts/
```

### Expected Response Structure

```json
{
  "cart_id": "abc123",
  "channel": "default-europe",
  "currency": "PLN",
  "items": [
    {
      "sku": "ENT-S001",
      "quantity": 1,
      "price": 500.00,
      "subtotal": 500.00
    }
  ],
  "subtotal": 500.00,
  "discounts": [
    {
      "code": "PERCENT10",
      "rule_name": "TEST_PERCENT_10",
      "modifier": "percent_discount",
      "value": 10,
      "amount": 50.00,
      "automatic": false,
      "combinable": false
    }
  ],
  "discount_total": 50.00,
  "shipping_cost": 9.99,
  "free_shipping": false,
  "total": 459.99,
  "gratis_available": []
}
```

## Running Tests

### Docker (Recommended)

```bash
# Full test suite
make test

# Discount tests only
make test-tags TAGS=@discount-rules

# With verbose output
make test-tags TAGS=@discount-rules VERBOSE=1

# Stop on first failure
make test-tags TAGS=@discount-rules STOP=1
```

### Standalone

```bash
cd repos/entirius-tests
uv venv && source .venv/bin/activate
uv pip install -e .

# Generate behave.ini
./scripts/generate-behave-ini.sh ../../.env

# Run tests
behave --tags=@discount-rules
behave --tags="@discount-rules and not @auth"
behave --tags=@discount-rules --stop
```

## Debugging Failed Tests

### 1. Check Fixture Import

```bash
docker exec entirius-docker-volkanos-1 python manage.py shell -c "
from django_checkout.models import DiscountRuleCode, DiscountCode
print(f'Rules: {DiscountRuleCode.objects.filter(name__startswith=\"TEST_\").count()}')
print(f'Codes: {DiscountCode.objects.filter(code__in=[\"PERCENT10\", \"PRICE50\"]).count()}')
"
```

Expected output: `Rules: 10`, `Codes: 9` (AUTO has no code)

### 2. Verify Discount via Django Admin

Navigate to: `http://localhost:8000/admin/django_checkout/discountrulecode/`

Check:
- Rule is active (`is_active=true`)
- Channel is `default-europe`
- Currency is `PLN`
- Code exists and is linked

### 3. Check API Response

```bash
# Create cart (example)
curl -X POST http://localhost:8000/api/v1/checkout/default-europe/cart/ \
  -H "Content-Type: application/json"

# Apply discount (example)
curl -X POST http://localhost:8000/api/v1/checkout/default-europe/cart/{cart_id}/discount/ \
  -H "Content-Type: application/json" \
  -d '{"code": "PERCENT10"}'
```

### 4. Check Test Output

Behave output shows:
- Which step failed
- Assertion error message
- Context variables (if configured)

Enable verbose output: `behave --verbose --tags=@discount-rules`

## Contributing

### Adding New Test Scenarios

1. Add scenario to `discount_rules.feature`
2. Run test (will fail with `NotImplementedError` if step not implemented)
3. Implement step in `discount_steps.py`
4. Verify test passes

### Modifying Discount Rules

1. Edit `fixtures/django_checkout.discounts.yaml`
2. Update `package/discount-rules.csv`
3. Update `DISCOUNT_RULES.md` documentation
4. Re-import: `./repos/entirius-test-package/scripts/entirius-docker-seed.sh`
5. Run tests to verify

## See Also

- `DISCOUNT_RULES.md` -- Fixture documentation
- `features/checkout/discount_rules.feature` -- BDD scenarios
- `AGENTS.md` -- Overall test architecture
- Django Checkout API documentation (TBD)
