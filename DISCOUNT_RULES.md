# Discount Rules Test Fixtures

Comprehensive test discount rules for automated testing of the Volkanos checkout discount system.

## Overview

The discount rules test package provides **10 discount rules** covering all major discount types and features:

- Percent discounts (simple and progressive)
- Fixed price discounts
- Gratis products (cheapest, most expensive, progressive)
- Free shipping
- Automatic application
- Combinable discounts
- User targeting (first order logged)

## Files

| File | Purpose |
|------|---------|
| `fixtures/django_checkout.discounts.yaml` | Django fixture (loaddata) -- discount rules and codes |
| `package/discount-rules.csv` | CSV metadata for BDD test verification |

## Fixture Structure

The fixture contains two model types:

1. **DiscountRuleCode** -- The discount rule definition
   - `name` -- Internal name (e.g., `TEST_PERCENT_10`)
   - `modifier` -- Discount type (e.g., `percent_discount`, `price_discount`, `cheapest_gratis`)
   - `extra_value` -- Discount value (percent, amount, or JSON for stepped discounts)
   - `min_order_amount` -- Minimum cart value to activate
   - `target` -- User targeting (`all`, `first_order_logged`)
   - `free_shipping` -- Boolean flag for free shipping
   - `combine_with_other_rules` -- Allow stacking with other discounts
   - `automatic_applications` -- Apply without code
   - `channels` -- List of channel PKs (2 = default-europe)
   - `currencies` -- List of currency PKs (1 = PLN)

2. **DiscountCode** -- User-facing discount code
   - `rule` -- FK to DiscountRuleCode
   - `code` -- The code users enter (e.g., `PERCENT10`)
   - `max_used` -- Usage limit (0 = unlimited)
   - `max_uses_per_user` -- Per-user limit (0 = unlimited)
   - `active_from` / `active_to` -- Date range (null = always active)

## Test Rules Reference

### 1. TEST_PERCENT_10 (Code: PERCENT10)
- **Type:** percent_discount
- **Value:** 10%
- **Min Order:** 0 PLN
- **Description:** Simple 10% discount, no minimum

### 2. TEST_PRICE_50 (Code: PRICE50)
- **Type:** price_discount
- **Value:** 50 PLN
- **Min Order:** 200 PLN
- **Description:** Fixed 50 PLN discount at minimum 200 PLN cart

### 3. TEST_CHEAPEST_GRATIS (Code: CHEAPEST_FREE)
- **Type:** cheapest_gratis
- **Value:** 1 item
- **Min Order:** 300 PLN
- **Description:** Cheapest product free at minimum 300 PLN

### 4. TEST_MOST_EXPENSIVE_GRATIS (Code: EXPENSIVE_FREE)
- **Type:** most_expensive_gratis
- **Value:** 1 item
- **Min Order:** 1000 PLN
- **Description:** Most expensive product free at minimum 1000 PLN

### 5. TEST_FREE_SHIPPING (Code: FREESHIP)
- **Type:** free_shipping (no modifier)
- **Value:** N/A
- **Min Order:** 200 PLN
- **Description:** Free shipping at minimum 200 PLN

### 6. TEST_STEP_PRICE_PERCENT (Code: STEP_PRICE_PCT)
- **Type:** step_price_percent_discount
- **Value:** Progressive (5% @ 200, 10% @ 500, 15% @ 1000, 20% @ 2000 PLN)
- **Min Order:** 0 PLN
- **Description:** Progressive discount by cart value

```json
{
  "PLN": {
    "200": 5,
    "500": 10,
    "1000": 15,
    "2000": 20
  }
}
```

### 7. TEST_GRATIS_STEPPED (Code: GRATIS_STEP)
- **Type:** gratis_stepped
- **Value:** Progressive (1 @ 300, 2 @ 600, 3 @ 1000 PLN)
- **Min Order:** 0 PLN
- **Description:** Progressive gratis products by cart value

```json
{
  "PLN": {
    "300": 1,
    "600": 2,
    "1000": 3
  }
}
```

### 8. TEST_AUTO_APPLY (Code: AUTO)
- **Type:** percent_discount
- **Value:** 5%
- **Min Order:** 1000 PLN
- **Combinable:** Yes
- **Automatic:** Yes
- **Description:** Automatic 5% discount at 1000 PLN, combinable with other discounts

### 9. TEST_FIRST_ORDER_LOGGED (Code: FIRST_LOGGED)
- **Type:** percent_discount
- **Value:** 20%
- **Min Order:** 0 PLN
- **Target:** first_order_logged
- **Description:** 20% discount for first order (logged users only)

### 10. TEST_COMBINABLE (Code: COMBINE50)
- **Type:** price_discount
- **Value:** 50 PLN
- **Min Order:** 500 PLN
- **Combinable:** Yes
- **Description:** Fixed 50 PLN discount, can be combined with other discounts

## Usage

### Import Fixtures

The discount rules are loaded automatically during `import-package.sh` (Step 1: Fixtures).

To load manually:

```bash
docker exec entirius-docker-volkanos-1 python manage.py loaddata \
  --format=yaml \
  /entirius/test-package/fixtures/django_checkout.discounts.yaml
```

### Verify Import

Check discount rules in Django Admin:
```
http://localhost:8000/admin/django_checkout/discountrulecode/
```

Or via Django shell:
```python
from django_checkout.models import DiscountRuleCode, DiscountCode

# List all test rules
DiscountRuleCode.objects.filter(name__startswith='TEST_').count()
# Should return: 10

# Get specific rule
rule = DiscountRuleCode.objects.get(name='TEST_PERCENT_10')
print(rule.modifier, rule.extra_value)
# Output: percent_discount 10

# Get discount code
code = DiscountCode.objects.get(code='PERCENT10')
print(code.rule.name)
# Output: TEST_PERCENT_10
```

### BDD Tests

Run discount rule tests:

```bash
# All discount tests
make test-tags TAGS=@discount-rules

# Import verification only
make test-tags TAGS="@discount-rules and @import-verification"

# Specific discount type
make test-tags TAGS="@discount-rules and @gratis"
```

## Adding New Test Rules

### 1. Add to Fixture (django_checkout.discounts.yaml)

```yaml
- model: django_checkout.discountrulecode
  pk: 110  # Use next available PK
  fields:
    name: TEST_MY_NEW_RULE
    modifier: percent_discount  # or other modifier
    extra_value: 15
    min_order_amount: '100.00'
    target: all
    is_active: true
    priority: 10
    channels:
    - 2  # default-europe
    currencies:
    - 1  # PLN

- model: django_checkout.discountcode
  pk: 110
  fields:
    rule: 110
    code: MYNEW15
    max_used: 0
```

### 2. Add to CSV (discount-rules.csv)

```csv
TEST_MY_NEW_RULE,MYNEW15,percent_discount,15,100,all,false,false,false,15% discount at min 100 PLN,15% rabatu przy min 100 PLN
```

### 3. Add BDD Test Scenario (discount_rules.feature)

```gherkin
Scenario: Apply 15% discount code at min 100 PLN
  Given I have an empty cart
  And I add products totaling at least 100 PLN
  When I apply discount code "MYNEW15"
  Then the discount should be applied successfully
  And the discount value should be 15 percent
```

### 4. Re-import

```bash
# From entirius-docker root
./repos/entirius-test-package/scripts/entirius-docker-seed.sh
```

## Discount Modifier Types Reference

| Modifier | Description | extra_value Format |
|----------|-------------|-------------------|
| `percent_discount` | Percentage off | Integer (e.g., 10 for 10%) |
| `price_discount` | Fixed amount off | Integer/Decimal (e.g., 50 for 50 PLN) |
| `cheapest_gratis` | N cheapest items free | Integer (number of items) |
| `most_expensive_gratis` | N most expensive items free | Integer (number of items) |
| `step_price_percent_discount` | Progressive % by cart value | JSON: `{"CURRENCY": {"threshold": percent, ...}}` |
| `gratis_stepped` | Progressive gratis by cart value | JSON: `{"CURRENCY": {"threshold": count, ...}}` |
| `null` (free_shipping=true) | Free shipping only | null |

## Target Types

| Target | Description |
|--------|-------------|
| `all` | All users (default) |
| `first_order_logged` | First order for logged-in users |
| `first_order_guest` | First order for guest users |
| `logged` | Logged-in users only |
| `guest` | Guest users only |

## Flags

| Flag | Description |
|------|-------------|
| `combine_with_other_rules` | Allow stacking with other discounts |
| `automatic_applications` | Apply without user entering code |
| `free_shipping` | Enable free shipping |
| `is_active` | Enable/disable rule |
| `show_when_invalid` | Show rule even when requirements not met |

## Channel and Currency Configuration

All test rules are configured for:
- **Channel:** `default-europe` (pk=2)
- **Currency:** `PLN` (pk=1)

To support other channels/currencies, add them to the `channels` and `currencies` lists in the fixture.

## Testing Checklist

When adding a new discount rule, verify:

- [ ] Fixture loads without errors (`loaddata`)
- [ ] Rule appears in Django Admin
- [ ] Code can be applied to cart (manual test)
- [ ] BDD test scenario passes
- [ ] Minimum order amount is enforced
- [ ] Discount calculation is correct
- [ ] Combinable flag is respected
- [ ] Automatic application works (if enabled)
- [ ] Target restrictions work (if applicable)

## Troubleshooting

### Fixture Load Errors

**Error:** `IntegrityError: duplicate key value violates unique constraint`

**Solution:** PKs in fixture conflict with existing data. Increment PK values (e.g., 110, 111, 112...).

### Discount Code Not Found

**Error:** API returns 404 or "code not found"

**Solution:** Verify DiscountCode model was created and linked to DiscountRuleCode. Check `code` field matches exactly.

### Discount Not Applied

**Possible causes:**
1. Cart below `min_order_amount`
2. Rule `is_active=false`
3. Channel/currency mismatch
4. Target restriction (e.g., `first_order_logged` but user not logged in)
5. Code expired (`active_to` date passed)

Check Django Admin and Django logs for details.

## See Also

- `/home/mnoworyta/entirius/service/entirius-docker/repos/entirius-tests/features/checkout/discount_rules.feature` -- BDD test scenarios
- `/home/mnoworyta/entirius/service/entirius-docker/repos/entirius-tests/features/checkout/steps/discount_steps.py` -- Step definitions
- Django Checkout documentation (to be added)
