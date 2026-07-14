# Quick Start: Discount Rule Testing

⚡ **TL;DR - Run Tests Now:**

```bash
# From entirius-docker directory
cd <docker-harness-root>

# Run all discount tests (13 scenarios, ~15 seconds)
make test-tags TAGS="@discount-rules"
```

---

## 🚀 Complete Setup from Scratch

### Prerequisites

1. **Docker environment running:**
   ```bash
   make up              # Start infrastructure + backend
   make health          # Verify all services healthy
   ```

2. **Test package imported:**
   ```bash
   make seed-fresh      # Full database reset + import test package
   # OR
   make import          # Import test package only (no DB reset)
   ```

3. **Verify import worked:**
   ```bash
   # Check discount codes exist
   docker exec entirius-docker-web-1 python manage.py shell -c "
   from django_checkout.models import DiscountCode
   print(f'Discount codes: {DiscountCode.objects.count()}')
   "
   ```

### Run Tests

```bash
# All discount tests
make test-tags TAGS="@discount-rules"

# Specific scenarios
make test-tags TAGS="@discount-rules and @import-verification"  # CSV verification only
make test-tags TAGS="@discount-rules and not @import"           # Skip import check
```

### Expected Results

```
✅ 1 feature passed, 0 failed
✅ 13 scenarios passed, 0 failed
✅ 98 steps passed, 0 failed
⏱️  Took ~15 seconds
```

---

## 📊 View Test Reports

### Console Output
```bash
# Full test output saved to file
make test-tags TAGS="@discount-rules" 2>&1 | tee /tmp/discount_test_report.txt

# View summary
make test-tags TAGS="@discount-rules" 2>&1 | grep -A 5 "feature passed"
```

### Test Coverage

**13 scenarios testing:**

1. **Import Verification** - CSV structure
2. **Simple Discounts** - percent_discount (10%)
3. **Price Discounts** - price_discount (50 EUR)
4. **Gratis Rules** - cheapest_gratis, most_expensive_gratis
5. **Progressive Discounts** - step_price_percent (10%, 15%, 20%)
6. **Progressive Gratis** - gratis_stepped (1, 3 items)
7. **Multi-Currency** - PERCENT_MULTI, PRICE_MULTI

---

## 🔧 Troubleshooting

### Tests fail with "discount code not found"

**Problem:** Discount codes not imported or max_used=0

**Fix:**
```bash
# Check if codes exist
docker exec entirius-docker-web-1 python manage.py shell -c "
from django_checkout.models import DiscountCode
codes = DiscountCode.objects.filter(code__in=['PERCENT10', 'PRICE50', 'GRATIS_STEP'])
for c in codes:
    print(f'{c.code}: max_used={c.max_used}, active={c.rule.is_active}')
"

# If max_used=0, update it:
docker exec entirius-docker-web-1 python manage.py shell -c "
from django_checkout.models import DiscountCode
DiscountCode.objects.filter(code__in=['PERCENT_MULTI', 'PRICE_MULTI']).update(max_used=999999)
print('Updated!')
"
```

### Tests fail with "API connection refused"

**Problem:** Backend not running

**Fix:**
```bash
make status           # Check if volkanos is running
make up               # Start if needed
make health           # Verify healthy
```

### Tests fail with "test package not imported"

**Problem:** CSV files missing or empty database

**Fix:**
```bash
make seed-fresh       # Full reset + import
```

---

## 📂 Project Structure

```
entirius-docker/
├── Makefile                              # make test-tags TAGS=...
└── repos/
    └── entirius-tests/                   # THIS REPO
        ├── features/
        │   ├── checkout/
        │   │   └── discount_rules.feature    # 13 BDD scenarios
        │   └── steps/
        │       └── discount_steps.py         # Step definitions (486 lines)
        ├── src/entirius_tests/
        │   ├── api_client.py                 # apply_discount() method
        │   └── csv_loader.py                 # load_discount_rules_csv()
        ├── QUICK_START_DISCOUNT_TESTS.md     # This file
        └── DISCOUNT_TESTING.md               # Full documentation
```

---

## 🧪 Example Test Scenarios

### Simple Percent Discount
```gherkin
Scenario: Apply 10% discount code to cart
  Given I have an empty cart
  And I add product "ENT-S001" with quantity 1 to cart
  When I apply discount code "PERCENT10"
  Then the discount should be applied successfully
  And the discount value should be 10 percent
```

### Price Discount with Minimum
```gherkin
Scenario: Apply 50 EUR discount when cart meets minimum
  Given I have an empty cart
  And I add products totaling at least 200 PLN
  When I apply discount code "PRICE50"
  Then the discount should be applied successfully
  And the discount amount should be 50 EUR
```

### Progressive Discount
```gherkin
Scenario: Progressive discount at 1000 PLN gives 15%
  Given I have an empty cart
  And I add products totaling at least 1000 PLN
  When I apply discount code "STEP_PRICE_PCT"
  Then the discount should be applied successfully
  And the discount value should be 15 percent
```

### Progressive Gratis
```gherkin
Scenario: Progressive gratis at 1000 PLN gives 3 items
  Given I have an empty cart
  And I add products totaling at least 1000 PLN
  When I apply discount code "GRATIS_STEP"
  Then 3 gratis products should be available
```

---

## 🔍 Step Definitions Reference

### Cart Setup
- `Given I have an empty cart` - Creates new cart
- `And I add product "{sku}" with quantity {n} to cart` - Add specific product
- `And I add products totaling at least {amount} PLN` - Auto-add products to reach threshold

### Apply Discount
- `When I apply discount code "{code}"` - POST to apply discount
- `When I calculate cart totals` - GET cart (for auto-apply discounts)

### Assertions
- `Then the discount should be applied successfully` - Check discount in cart.discounts
- `And the discount type should be "{modifier}"` - Verify modifier type
- `And the discount value should be {n} percent` - Calculate actual % from response
- `And the discount amount should be {n} EUR` - Check fixed discount amount
- `And {n} gratis products should be available` - Check gratis_rules[].max_available_quantity

---

## 📋 Discount Codes Available

| Code | Type | Value | Min Order | Description |
|------|------|-------|-----------|-------------|
| `PERCENT10` | percent_discount | 10% | 0 EUR | Simple 10% |
| `PRICE50` | price_discount | 50 EUR | 200 EUR | Fixed 50 EUR |
| `CHEAPEST_FREE` | cheapest_gratis | 1 item | 300 EUR | Cheapest free |
| `EXPENSIVE_FREE` | most_expensive_gratis | 1 item | 1000 EUR | Most expensive free |
| `STEP_PRICE_PCT` | step_price_percent | 10/15/20% | 500/1000/2000 EUR | Progressive % |
| `GRATIS_STEP` | gratis_stepped | 1/3 items | 300/1000 EUR | Progressive gratis |
| `PERCENT_MULTI` | percent_discount | 10% | 0 EUR | Multi-currency |
| `PRICE_MULTI` | price_discount | 20 EUR | 0 EUR | Multi-currency |

---

## 🎯 Test Execution Flow

```
1. make test-tags TAGS="@discount-rules"
   ↓
2. Docker compose starts tests container (python:3.12-slim)
   ↓
3. Container waits for API (http://volkanos:8000)
   ↓
4. Installs entirius-tests package (pip install -e .)
   ↓
5. Runs behave with --tags=@discount-rules
   ↓
6. Each scenario:
   - Background: import verification + channel setup
   - Given: create cart, add products
   - When: apply discount code (POST /api/checkout/v1/{channel}/carts/{cart_id}/discounts/)
   - Then: verify response (discount_amount, gratis_rules, etc.)
   ↓
7. Output: Pretty format + summary stats
```

---

## 🚢 CI/CD Integration

### CI example
```yaml
test:discount-rules:
  stage: test
  script:
    - make up
    - make seed-fresh
    - make test-tags TAGS="@discount-rules"
  artifacts:
    when: always
    reports:
      junit: repos/entirius-tests/reports/*.xml
```

---

## 📖 Full Documentation

- **This file** - Quick start, troubleshooting
- `DISCOUNT_TESTING.md` - Complete testing guide
- `features/checkout/discount_rules.feature` - All test scenarios
- `features/steps/discount_steps.py` - Step implementations

---

## ✅ Quick Checklist

**First time setup:**
- [ ] `make up` - Start Docker environment
- [ ] `make seed-fresh` - Import test data
- [ ] `make test-tags TAGS="@discount-rules"` - Run tests

**Verify working:**
- [ ] All 13 scenarios pass
- [ ] Execution time ~15 seconds
- [ ] No "connection refused" errors

**Troubleshooting:**
- [ ] Check `make status` - all services running
- [ ] Check `make health` - all services healthy
- [ ] Check discount codes exist in database

---

## 🆘 Common Commands

```bash
# Start environment
make up

# Check status
make status
make health

# Import test data
make seed-fresh          # Full reset
make import              # Import only

# Run tests
make test-tags TAGS="@discount-rules"                    # All discount tests
make test-tags TAGS="@discount-rules and @import"        # Import verification
make test-tags TAGS="@checkout"                          # All checkout tests

# Debug
docker exec entirius-docker-web-1 python manage.py shell
docker logs entirius-docker-web-1
```

---

**Need help?** See `DISCOUNT_TESTING.md` for detailed documentation.
