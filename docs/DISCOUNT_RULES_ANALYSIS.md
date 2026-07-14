# Comprehensive Analysis: Volkanos Discount Rules & Gratis System

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Model Architecture](#model-architecture)
3. [Discount Rule Types](#discount-rule-types)
4. [Gratis System Deep Dive](#gratis-system-deep-dive)
5. [Product Filtering](#product-filtering)
6. [Configuration Examples](#configuration-examples)
7. [Missing Test Coverage](#missing-test-coverage)

---

## Executive Summary

The Volkanos discount system consists of three core models:

1. **DiscountRuleCode** - The main discount rule configuration
2. **DiscountModeOfAction (GratisProductFilter)** - Defines which products are ELIGIBLE for gratis selection or discount application
3. **ThresholdProductFilter** - Defines which products COUNT toward the threshold calculation

### Key Findings

**What we had:**
- Basic gratis rules (cheapest/most expensive/stepped)
- Simple percent and price discounts
- Free shipping rules
- Auto-apply and combinable rules
- First-order targeting

**What we missed:**
- ✗ Quantity-based progressive discounts (per line/whole cart)
- ✗ Fixed price per currency discounts
- ✗ DiscountModeOfAction configuration for gratis product pools
- ✗ ThresholdProductFilter for selective threshold calculation
- ✗ Product filtering by categories, attributes, price ranges
- ✗ Multi-currency support for all rule types
- ✗ Complex filter combinations (inclusion/exclusion, take_common_part)

---

## Model Architecture

### 1. DiscountRuleCode

**Location**: `repos/django-apps/django-checkout/src/django_checkout/models/discount_rule_code.py`

**Purpose**: Main discount rule configuration

**Key Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(128) | Internal rule name (e.g., "TEST_PERCENT_10") |
| `modifier` | CharField | Discount type (see [Modifiers](#modifiers)) |
| `extra_value` | JSONField | Configuration for modifier (int/dict/list) |
| `target` | CharField | Who can use: "all", "first_order_logged", "first_order_all" |
| `min_order_amount` | Decimal(12,2) | Minimum cart value to activate |
| `free_shipping` | Boolean | Grant free shipping |
| `free_order` | Boolean | Entire order free |
| `is_omnibus` | Boolean | Include in omnibus price calculations |
| `priority` | PositiveSmallInt | Lower = higher priority |
| `combine_with_other_rules` | Boolean | Can stack with other discounts |
| `automatic_applications` | Boolean | Auto-apply without code |
| `is_active` | Boolean | Rule enabled/disabled |
| `show_when_invalid` | Boolean | Show gratis rule even when conditions not met |
| `extension` | JSONField | Marketing copy, custom data |
| `channels` | M2M | Which sales channels |
| `currencies` | M2M | Which currencies (blank = all) |
| `free_shipping_methods` | M2M | Specific shipping methods for free shipping |

**Related Models**:
- `discount_mode_of_actions_rule` → **DiscountModeOfAction** (which products get discount/gratis)
- `threshold_filters` → **ThresholdProductFilter** (which products count toward threshold)
- `codes` → **DiscountCode** (user-facing codes)

---

### 2. DiscountModeOfAction (GratisProductFilter)

**Location**: `repos/django-apps/django-checkout/src/django_checkout/models/discount_mode_of_actions.py`

**Purpose**:
- **For gratis rules**: Defines which products user can SELECT as gratis
- **For regular discounts**: Defines which products receive the discount

**Extends**: `AbstractProductFilter` (see [Product Filtering](#product-filtering))

**How it works**:

```python
# Example: User can choose ANY laptop as gratis
gratis_rule = DiscountRuleCode.objects.create(
    name="LAPTOP_GRATIS",
    modifier=ModifiersForDiscountRule.GRATIS_STEPPED,
    extra_value={"PLN": {"500": 1}},  # 1 gratis at 500 PLN
)

# Define available gratis products (laptops category)
mode_of_action = DiscountModeOfAction.objects.create(
    rule=gratis_rule,
    is_inclusion_or_exclusion=FilterModeType.INCLUSION,  # Include these
)
mode_of_action.categories.add(laptops_category)
```

Now when user reaches 500 PLN threshold, they can SELECT any laptop as their gratis item.

**Key Difference**:
- **Without DiscountModeOfAction**: Gratis = cheapest/most expensive from entire cart
- **With DiscountModeOfAction**: Gratis = user picks from filtered product pool

---

### 3. ThresholdProductFilter

**Location**: `repos/django-apps/django-checkout/src/django_checkout/models/discount_mode_of_actions.py`

**Purpose**: Filter which products COUNT toward gratis/discount threshold

**Extends**: `AbstractProductFilter` (see [Product Filtering](#product-filtering))

**How it works**:

```python
# Example: Only electronics count toward 500 PLN gratis threshold
gratis_rule = DiscountRuleCode.objects.create(
    name="ELECTRONICS_GRATIS",
    modifier=ModifiersForDiscountRule.GRATIS_STEPPED,
    extra_value={"PLN": {"500": 1}},
)

# Only electronics count toward threshold
threshold_filter = ThresholdProductFilter.objects.create(
    rule=gratis_rule,
    is_inclusion_or_exclusion=FilterModeType.INCLUSION,
)
threshold_filter.categories.add(electronics_category)

# User can pick any accessory as gratis
mode_of_action = DiscountModeOfAction.objects.create(
    rule=gratis_rule,
    is_inclusion_or_exclusion=FilterModeType.INCLUSION,
)
mode_of_action.categories.add(accessories_category)
```

**Result**: User needs 500 PLN worth of electronics in cart, then gets to pick an accessory for free.

---

### 4. AbstractProductFilter

**Location**: `repos/django-apps/django-checkout/src/django_checkout/models/abstract_product_filter.py`

**Purpose**: Base class for both DiscountModeOfAction and ThresholdProductFilter

**Filter Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `products` | M2M(Product) | Specific products (if configurable, includes children) |
| `categories` | M2M(ProductCategory) | Products in these categories |
| `attributes` | M2M(Attribute) | Products with these attributes |
| `features_qty_greater_than_attr_value` | M2M(Feature) | Qty > attribute value |
| `features_qty_is_multiple_of_attr_value` | M2M(Feature) | Qty is multiple of attribute value |
| `product_price_from` | PositiveInt | Min product unit price |
| `product_price_to` | PositiveInt | Max product unit price |
| `cart_price_from` | PositiveInt | Min total cart price |
| `cart_price_to` | PositiveInt | Max total cart price |
| `qty_from` | PositiveInt | Min product quantity |
| `qty_to` | PositiveInt | Max product quantity |
| `cart_qty_from` | PositiveInt | Min total cart quantity |
| `cart_qty_to` | PositiveInt | Max total cart quantity |
| `is_inclusion_or_exclusion` | CharField | "inclusion" or "exclusion" |
| `take_common_part` | Boolean | AND vs OR logic (see below) |

**Filter Logic**:

```
take_common_part=True  → Filters combined with AND (common part)
take_common_part=False → Filters combined with OR  (union)

is_inclusion_or_exclusion="inclusion" → Include matching products
is_inclusion_or_exclusion="exclusion" → Exclude matching products
```

**Example Complex Filter**:

```python
# Include: (laptops OR tablets) AND price 1000-5000 PLN
filter1 = DiscountModeOfAction.objects.create(
    rule=rule,
    is_inclusion_or_exclusion=FilterModeType.INCLUSION,
    take_common_part=True,
    product_price_from=1000,
    product_price_to=5000,
)
filter1.categories.add(laptops, tablets)

# Exclude: gaming laptops
filter2 = DiscountModeOfAction.objects.create(
    rule=rule,
    is_inclusion_or_exclusion=FilterModeType.EXCLUSION,
    take_common_part=False,
)
filter2.attributes.add(gaming_attribute)
```

---

## Discount Rule Types

### Modifiers

All available discount modifiers from `ModifiersForDiscountRule`:

| Modifier | Description | extra_value Format |
|----------|-------------|--------------------|
| **Basic Discounts** |
| `percent_discount` | Fixed % off | `10` or `{"PLN": 15, "EUR": 10}` |
| `price_discount` | Fixed amount off | `50` or `{"PLN": 100, "EUR": 20}` |
| **Quantity-Based Progressive** |
| `step_qty_percent_discount` | % off per product line based on qty | `{"1": 5, "3": 10, "5": 15}` |
| `step_qty_percent_discount_whole_cart` | % off based on total cart qty | `{"10": 5, "20": 10}` or `{"PLN": {"10": 5}}` |
| `step_qty_price_discount_whole_cart` | Fixed amount off based on cart qty | `{"5": 50, "10": 120}` or `{"PLN": {"5": 50}}` |
| `step_qty_fixed_price_per_currency` | Fixed unit price at qty threshold | `{"PLN": {"2": 89.99, "5": 69.99}}` |
| **Price-Based Progressive** |
| `step_price_percent_discount` | % off based on cart total | `{"PLN": {"200": 5, "500": 10}}` |
| **Gratis (Free Products)** |
| `cheapest_gratis` | N cheapest items free (auto) | `1` (number of items) |
| `most_expensive_gratis` | N most expensive items free (auto) | `1` (number of items) |
| `gratis_stepped` | Progressive gratis (user picks) | `{"PLN": {"300": 1, "600": 2}}` |
| `gratis_by_sku_in_cart` | Gratis if specific SKUs in cart | `["SKU1", "SKU2"]` (required SKUs) |

### Targets

| Target | Description | Use Case |
|--------|-------------|----------|
| `all` | Everyone | Standard promotions |
| `first_order_logged` | Logged users, no prior orders | Welcome discount for registered users |
| `first_order_all` | Anyone (logged/guest), no prior orders by email | Welcome discount for all |

---

## Gratis System Deep Dive

### How Gratis Works

**The Flow**:

1. **Threshold Calculation**:
   - If `ThresholdProductFilter` exists: Only matching products count toward `min_order_amount`
   - Otherwise: All cart products count

2. **Gratis Availability Check**:
   - Threshold met?
   - For `gratis_by_sku_in_cart`: Are all required SKUs in cart?

3. **Gratis Product Pool**:
   - If `DiscountModeOfAction` exists: User picks from filtered products
   - Otherwise: System auto-selects (cheapest/most expensive from cart)

4. **User Selection** (for `gratis_stepped` and `gratis_by_sku_in_cart`):
   - Frontend calls `/api/v1/checkout/{channel}/gratis-rules/{cart_id}/` to get available gratis
   - User picks SKU and quantity
   - Adds to cart via discount code with `sku` and `quantity` fields

**Gratis Price Calculation**:

From `calc_base_unit_price_for_gratis()`:

```python
gratis_multiplier = Decimal(1 - (settings.GRATIS_PERCENT_DISCOUNT / 100))
base_price = unit_price * gratis_multiplier

# If result < GRATIS_PRICE, use GRATIS_PRICE instead
# Default: GRATIS_PRICE = 0.01 PLN, GRATIS_PERCENT_DISCOUNT = 100 (free)
```

**Gratis Mechanisms**:

```python
GRATIS_MECHANISM = 1  # Apply GRATIS_PERCENT_DISCOUNT, min GRATIS_PRICE
GRATIS_MECHANISM = 2  # Always use GRATIS_PRICE (fixed 0.01 PLN)
```

### Gratis Rule Variants

#### 1. cheapest_gratis / most_expensive_gratis

**Automatic** - system picks cheapest/most expensive from cart.

```yaml
- model: django_checkout.discountrulecode
  fields:
    name: CHEAPEST_GRATIS
    modifier: cheapest_gratis
    extra_value: 1  # Number of items
    min_order_amount: 300.00
```

**No DiscountModeOfAction needed** - works on existing cart items.

#### 2. gratis_stepped

**User picks** from available product pool.

```yaml
- model: django_checkout.discountrulecode
  fields:
    name: GRATIS_STEPPED
    modifier: gratis_stepped
    extra_value:
      PLN:
        '300': 1  # 1 gratis at 300 PLN
        '600': 2  # 2 gratis at 600 PLN
        '1000': 3  # 3 gratis at 1000 PLN

# Optional: Limit gratis product pool
- model: django_checkout.discountmodeofaction
  fields:
    rule: <rule_id>
    is_inclusion_or_exclusion: inclusion
  # Add categories, products, attributes via M2M
```

**Frontend Flow**:
```
1. GET /api/v1/checkout/{channel}/gratis-rules/{cart_id}/
   → Returns: {"items": [{"sku": "GIFT1", "price": 0.01}, ...], "code": "GRATIS300", ...}

2. User selects SKU "GIFT1", quantity 1

3. POST /api/v1/checkout/{channel}/cart/{cart_id}/discounts/
   Body: {"code": "GRATIS300", "sku": "GIFT1", "quantity": 1}
```

#### 3. gratis_by_sku_in_cart

**User picks** from product pool, but only if specific SKUs are in cart.

```yaml
- model: django_checkout.discountrulecode
  fields:
    name: GRATIS_BY_SKU
    modifier: gratis_by_sku_in_cart
    extra_value: ["LAPTOP-X", "LAPTOP-Y"]  # Must have these in cart
    min_order_amount: 1000.00

# Define available gratis products
- model: django_checkout.discountmodeofaction
  fields:
    rule: <rule_id>
    is_inclusion_or_exclusion: inclusion
  # Add products/categories
```

**Logic**: All SKUs from `extra_value` must be in cart, then user can pick gratis from `DiscountModeOfAction` filtered products.

---

## Product Filtering

### Use Cases

1. **DiscountModeOfAction** for gratis → "What can user pick?"
2. **DiscountModeOfAction** for discount → "What gets discounted?"
3. **ThresholdProductFilter** → "What counts toward threshold?"

### Example: Category-Based Gratis

```yaml
# Spend 500 PLN on electronics, get any accessory free

# Rule
- model: django_checkout.discountrulecode
  pk: 200
  fields:
    name: ELECTRONICS_PROMO
    modifier: gratis_stepped
    extra_value:
      PLN: {'500': 1}

# Threshold: Only electronics count
- model: django_checkout.thresholdproductfilter
  pk: 201
  fields:
    rule: 200
    is_inclusion_or_exclusion: inclusion
    # M2M: categories = [electronics_category]

# Gratis pool: Only accessories available
- model: django_checkout.discountmodeofaction
  pk: 202
  fields:
    rule: 200
    is_inclusion_or_exclusion: inclusion
    # M2M: categories = [accessories_category]
```

### Example: Attribute-Based Discount

```yaml
# 20% off all "premium" products

- model: django_checkout.discountrulecode
  pk: 300
  fields:
    name: PREMIUM_DISCOUNT
    modifier: percent_discount
    extra_value: 20

- model: django_checkout.discountmodeofaction
  pk: 301
  fields:
    rule: 300
    is_inclusion_or_exclusion: inclusion
    # M2M: attributes = [premium_attribute]
```

### Example: Price Range Filter

```yaml
# 10% off products priced 100-500 PLN

- model: django_checkout.discountmodeofaction
  pk: 400
  fields:
    rule: <rule_id>
    is_inclusion_or_exclusion: inclusion
    product_price_from: 100
    product_price_to: 500
```

### Example: Exclusion Filter

```yaml
# 15% off everything EXCEPT sale items

- model: django_checkout.discountrulecode
  pk: 500
  fields:
    name: REGULAR_ITEMS_SALE
    modifier: percent_discount
    extra_value: 15

# Exclude sale category
- model: django_checkout.discountmodeofaction
  pk: 501
  fields:
    rule: 500
    is_inclusion_or_exclusion: exclusion
    # M2M: categories = [sale_category]
```

---

## Configuration Examples

### Multi-Currency Support

All modifiers support multi-currency `extra_value`:

```yaml
# Single currency (old format, works for all)
extra_value: 10

# Multi-currency simple
extra_value:
  PLN: 15
  EUR: 10
  USD: 12

# Multi-currency progressive
extra_value:
  PLN:
    '200': 5   # 5% at 200 PLN
    '500': 10  # 10% at 500 PLN
  EUR:
    '50': 5    # 5% at 50 EUR
    '100': 10  # 10% at 100 EUR
```

### Complex Filter Combinations

```python
# Rule: 20% off laptops priced 2000-8000 PLN, exclude gaming series

rule = DiscountRuleCode.objects.create(
    name="LAPTOP_SALE",
    modifier=ModifiersForDiscountRule.PERCENT_DISCOUNT,
    extra_value={"PLN": 20, "EUR": 18},
)

# Include laptops 2000-8000 PLN
f1 = DiscountModeOfAction.objects.create(
    rule=rule,
    is_inclusion_or_exclusion=FilterModeType.INCLUSION,
    take_common_part=True,  # AND logic
    product_price_from=2000,
    product_price_to=8000,
)
f1.categories.add(laptops_category)

# Exclude gaming series
f2 = DiscountModeOfAction.objects.create(
    rule=rule,
    is_inclusion_or_exclusion=FilterModeType.EXCLUSION,
    take_common_part=False,  # OR logic
)
f2.attributes.add(gaming_series_attribute)
```

### Stepped Gratis with Threshold Filter

```yaml
# Spend 300 PLN on cosmetics, get 1 sample free
# Spend 600 PLN on cosmetics, get 2 samples free

- model: django_checkout.discountrulecode
  pk: 600
  fields:
    name: COSMETICS_SAMPLES
    modifier: gratis_stepped
    extra_value:
      PLN:
        '300': 1
        '600': 2

# Only cosmetics count toward threshold
- model: django_checkout.thresholdproductfilter
  pk: 601
  fields:
    rule: 600
    is_inclusion_or_exclusion: inclusion
    # M2M: categories = [cosmetics_category]

# Only samples available as gratis
- model: django_checkout.discountmodeofaction
  pk: 602
  fields:
    rule: 600
    is_inclusion_or_exclusion: inclusion
    # M2M: categories = [samples_category]
```

---

## Missing Test Coverage

### Current Fixtures (10 rules)

✓ `percent_discount` (simple)
✓ `price_discount` (simple)
✓ `cheapest_gratis` (auto)
✓ `most_expensive_gratis` (auto)
✓ `step_price_percent_discount` (progressive price-based)
✓ `gratis_stepped` (user picks, no filters)
✓ Free shipping
✓ Auto-apply
✓ First order logged
✓ Combinable

### Missing Variants

#### 1. Quantity-Based Discounts
- ✗ `step_qty_percent_discount` (per line)
- ✗ `step_qty_percent_discount_whole_cart` (single currency)
- ✗ `step_qty_percent_discount_whole_cart` (multi-currency)
- ✗ `step_qty_price_discount_whole_cart` (single currency)
- ✗ `step_qty_price_discount_whole_cart` (multi-currency)
- ✗ `step_qty_fixed_price_per_currency`

#### 2. Gratis with Filters
- ✗ `gratis_stepped` + `DiscountModeOfAction` (limited gratis pool)
- ✗ `gratis_stepped` + `ThresholdProductFilter` (selective threshold)
- ✗ `gratis_stepped` + both filters (complex scenario)
- ✗ `gratis_by_sku_in_cart` (conditional gratis)
- ✗ `cheapest_gratis` + `ThresholdProductFilter`
- ✗ `most_expensive_gratis` + `ThresholdProductFilter`

#### 3. Product Filter Variants
- ✗ Category-based discount (DiscountModeOfAction)
- ✗ Attribute-based discount
- ✗ Price range filter
- ✗ Quantity range filter
- ✗ Exclusion filter
- ✗ Combined filters (AND/OR logic)
- ✗ `take_common_part` variants

#### 4. Multi-Currency
- ✗ Multi-currency `percent_discount`
- ✗ Multi-currency `price_discount`
- ✗ Multi-currency quantity-based discounts

#### 5. Edge Cases
- ✗ Multiple gratis rules active simultaneously
- ✗ Gratis out of stock handling
- ✗ Invalid gratis selection (SKU not in pool)
- ✗ Threshold filter with empty result
- ✗ Mode of action filter with empty result
- ✗ Expired rules with `show_when_invalid`
- ✗ Max uses per user
- ✗ Limited total uses

---

## Test Coverage Matrix

| Feature | Tested | Priority |
|---------|--------|----------|
| **Basic Discounts** |
| Percent (simple) | ✓ | - |
| Percent (multi-currency) | ✗ | HIGH |
| Price (simple) | ✓ | - |
| Price (multi-currency) | ✗ | HIGH |
| **Quantity Discounts** |
| Step qty % (per line) | ✗ | HIGH |
| Step qty % (cart, single currency) | ✗ | HIGH |
| Step qty % (cart, multi-currency) | ✗ | MEDIUM |
| Step qty price (cart) | ✗ | HIGH |
| Step qty fixed price | ✗ | MEDIUM |
| **Price Discounts** |
| Step price % | ✓ | - |
| **Gratis Auto** |
| Cheapest | ✓ | - |
| Most expensive | ✓ | - |
| **Gratis User-Select** |
| Stepped (no filters) | ✓ | - |
| Stepped + ModeOfAction | ✗ | CRITICAL |
| Stepped + ThresholdFilter | ✗ | CRITICAL |
| Stepped + both filters | ✗ | HIGH |
| By SKU in cart | ✗ | HIGH |
| **Product Filters** |
| Category inclusion | ✗ | CRITICAL |
| Category exclusion | ✗ | HIGH |
| Attribute filter | ✗ | HIGH |
| Price range filter | ✗ | MEDIUM |
| Combined filters | ✗ | MEDIUM |
| **Targets** |
| All | ✓ | - |
| First order logged | ✓ | - |
| First order all | ✗ | LOW |
| **Features** |
| Free shipping | ✓ | - |
| Auto-apply | ✓ | - |
| Combinable | ✓ | - |
| show_when_invalid | ✗ | MEDIUM |
| Max uses | ✗ | MEDIUM |
| Extension data | ✗ | LOW |

**CRITICAL Priority**: Core functionality for gratis selection UX
**HIGH Priority**: Common use cases
**MEDIUM Priority**: Advanced features
**LOW Priority**: Edge cases

---

## Next Steps

1. **Expand fixtures** (`django_checkout.discounts.yaml`):
   - Add 20+ new rules covering all modifiers
   - Add DiscountModeOfAction examples
   - Add ThresholdProductFilter examples
   - Add product/category fixtures for filters

2. **Expand BDD scenarios** (`discount_rules.feature`):
   - Quantity-based discount scenarios
   - Gratis selection flow scenarios
   - Product filter scenarios
   - Multi-currency scenarios
   - Edge case scenarios

3. **Add step definitions** (`discount_steps.py`):
   - Gratis selection steps
   - Product filter validation steps
   - Multi-currency assertion steps

4. **Add CSV metadata** (`discounts.csv`):
   - Document all test discount rules
   - Include expected behavior descriptions

5. **Documentation**:
   - Admin guide for creating discount rules
   - Frontend integration guide for gratis selection
   - Troubleshooting guide

---

## References

- **Models**: `repos/django-apps/django-checkout/src/django_checkout/models/`
- **Business Logic**: `repos/django-apps/django-checkout/src/django_checkout/worker/discount_worker.py`
- **Gratis Logic**: `repos/django-apps/django-checkout/src/django_checkout/worker/gratis.py`
- **Validation**: `repos/django-apps/django-checkout/src/django_checkout/domain/validators/discounts.py`
- **Management Command**: `repos/django-apps/django-checkout/src/django_checkout/management/commands/create_all_discount_rules.py`
- **Test Examples**: `repos/django-apps/django-checkout/src/django_checkout/test/fixtures/discount_rules_currency_examples.json`
