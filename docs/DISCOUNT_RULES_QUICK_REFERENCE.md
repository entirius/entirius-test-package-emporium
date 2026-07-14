# Discount Rules - Quick Reference Guide

## Configuration Examples

### Basic Discounts

#### 10% Off Everything
```yaml
- model: django_checkout.discountrulecode
  fields:
    name: SPRING_SALE
    modifier: percent_discount
    extra_value: 10
    min_order_amount: '0.00'
    target: all

- model: django_checkout.discountcode
  fields:
    code: SPRING10
```

#### 50 PLN Off at 200 PLN
```yaml
- model: django_checkout.discountrulecode
  fields:
    name: DISCOUNT_50
    modifier: price_discount
    extra_value: 50
    min_order_amount: '200.00'
```

#### Multi-Currency Discount
```yaml
- model: django_checkout.discountrulecode
  fields:
    name: GLOBAL_SALE
    modifier: percent_discount
    extra_value:
      PLN: 15
      EUR: 10
      USD: 12
    currencies: [1, 2, 3]  # PLN, EUR, USD
```

### Quantity-Based Discounts

#### Buy More, Save More (Per Line)
```yaml
# 1-2 pcs = 5%, 3-4 pcs = 10%, 5+ pcs = 15%
- model: django_checkout.discountrulecode
  fields:
    name: BULK_DISCOUNT
    modifier: step_qty_percent_discount
    extra_value:
      '1': 5
      '3': 10
      '5': 15
```

#### Cart Quantity Discount
```yaml
# Total cart: 10 pcs = 5%, 20 pcs = 10%
- model: django_checkout.discountrulecode
  fields:
    name: CART_QTY_DISCOUNT
    modifier: step_qty_percent_discount_whole_cart
    extra_value:
      '10': 5
      '20': 10
      '50': 15
```

#### Wholesale Pricing
```yaml
# 2 pcs = 89.99 each, 5 pcs = 69.99 each
- model: django_checkout.discountrulecode
  fields:
    name: WHOLESALE
    modifier: step_qty_fixed_price_per_currency
    extra_value:
      PLN:
        '2': 89.99
        '5': 69.99
        '10': 59.99
```

### Price-Based Progressive

#### Spend More, Save More
```yaml
- model: django_checkout.discountrulecode
  fields:
    name: PROGRESSIVE_SALE
    modifier: step_price_percent_discount
    extra_value:
      PLN:
        '200': 5    # 200 PLN = 5% off
        '500': 10   # 500 PLN = 10% off
        '1000': 15  # 1000 PLN = 15% off
```

### Gratis (Free Products)

#### Auto-Select Cheapest
```yaml
- model: django_checkout.discountrulecode
  fields:
    name: CHEAPEST_FREE
    modifier: cheapest_gratis
    extra_value: 1  # 1 item free
    min_order_amount: '300.00'
```

#### User Selects - Simple
```yaml
# Spend 300 PLN, pick 1 free item (any product)
- model: django_checkout.discountrulecode
  fields:
    name: GRATIS_300
    modifier: gratis_stepped
    extra_value:
      PLN:
        '300': 1  # 1 free at 300
        '600': 2  # 2 free at 600
```

#### User Selects - Filtered Pool
```yaml
# Spend 500 PLN, pick 1 free ottoman

- model: django_checkout.discountrulecode
  pk: 200
  fields:
    name: FREE_OTTOMAN
    modifier: gratis_stepped
    extra_value:
      PLN:
        '500': 1

# Limit gratis to ottomans only
- model: django_checkout.discountmodeofaction
  pk: 200
  fields:
    rule: 200
    is_inclusion_or_exclusion: inclusion
    # M2M: categories.add(ottomans_category)
```

#### Conditional Gratis
```yaml
# If cart contains SOFA-A AND SOFA-B, get free gift

- model: django_checkout.discountrulecode
  fields:
    name: SOFA_BUNDLE_GIFT
    modifier: gratis_by_sku_in_cart
    extra_value:
      - SOFA-A
      - SOFA-B
    extension:
      quantity: 1
    min_order_amount: '1000.00'

# User can pick from gift category
- model: django_checkout.discountmodeofaction
  fields:
    rule: <rule_id>
    is_inclusion_or_exclusion: inclusion
    # M2M: categories.add(gifts_category)
```

#### Spend-on-X-Get-Free-Y
```yaml
# Spend 500 PLN on sofas, get free accessory

- model: django_checkout.discountrulecode
  pk: 300
  fields:
    name: SOFA_PROMO
    modifier: gratis_stepped
    extra_value:
      PLN:
        '500': 1

# Only sofas count toward threshold
- model: django_checkout.thresholdproductfilter
  pk: 300
  fields:
    rule: 300
    is_inclusion_or_exclusion: inclusion
    # M2M: categories.add(sofas_category)

# User can pick from accessories
- model: django_checkout.discountmodeofaction
  pk: 300
  fields:
    rule: 300
    is_inclusion_or_exclusion: inclusion
    # M2M: categories.add(accessories_category)
```

### Product Filtering

#### Discount Specific Category
```yaml
# 20% off all chairs

- model: django_checkout.discountrulecode
  pk: 400
  fields:
    name: CHAIRS_SALE
    modifier: percent_discount
    extra_value: 20

- model: django_checkout.discountmodeofaction
  pk: 400
  fields:
    rule: 400
    is_inclusion_or_exclusion: inclusion
    # M2M: categories.add(chairs_category)
```

#### Discount Price Range
```yaml
# 15% off products priced 500-2000 PLN

- model: django_checkout.discountrulecode
  pk: 500
  fields:
    name: MIDRANGE_SALE
    modifier: percent_discount
    extra_value: 15

- model: django_checkout.discountmodeofaction
  pk: 500
  fields:
    rule: 500
    is_inclusion_or_exclusion: inclusion
    product_price_from: 500
    product_price_to: 2000
```

#### Exclude Category
```yaml
# 10% off everything EXCEPT sale items

- model: django_checkout.discountrulecode
  pk: 600
  fields:
    name: REGULAR_ITEMS_SALE
    modifier: percent_discount
    extra_value: 10

- model: django_checkout.discountmodeofaction
  pk: 600
  fields:
    rule: 600
    is_inclusion_or_exclusion: exclusion  # EXCLUDE
    # M2M: categories.add(sale_category)
```

#### Complex Filter (AND Logic)
```yaml
# 25% off expensive sofas (category=sofas AND price>1000)

- model: django_checkout.discountrulecode
  pk: 700
  fields:
    name: PREMIUM_SOFAS
    modifier: percent_discount
    extra_value: 25

- model: django_checkout.discountmodeofaction
  pk: 700
  fields:
    rule: 700
    is_inclusion_or_exclusion: inclusion
    take_common_part: true  # AND logic
    product_price_from: 1000
    # M2M: categories.add(sofas_category)
```

### Special Rules

#### Welcome Discount (First Order)
```yaml
- model: django_checkout.discountrulecode
  fields:
    name: WELCOME20
    modifier: percent_discount
    extra_value: 20
    target: first_order_logged  # Only logged users, first order
```

#### Auto-Apply
```yaml
# Automatically applied, no code needed
- model: django_checkout.discountrulecode
  fields:
    name: AUTO_5PCT
    modifier: percent_discount
    extra_value: 5
    min_order_amount: '1000.00'
    automatic_applications: true  # Auto-apply
    combine_with_other_rules: true  # Can stack

# No DiscountCode needed for auto-apply
```

#### Combinable Discount
```yaml
- model: django_checkout.discountrulecode
  fields:
    name: STACKABLE_50
    modifier: price_discount
    extra_value: 50
    min_order_amount: '500.00'
    combine_with_other_rules: true  # Can combine with others
```

#### Limited Uses
```yaml
- model: django_checkout.discountcode
  fields:
    code: FLASH30
    max_used: 100  # Total uses: 100
    max_uses_per_user: 1  # Each user: once
```

#### Free Shipping
```yaml
- model: django_checkout.discountrulecode
  fields:
    name: FREE_SHIP_200
    free_shipping: true
    modifier: null  # No discount modifier
    min_order_amount: '200.00'
```

## Testing Quick Reference

### Test Gratis Selection Flow

```python
# 1. Get available gratis
GET /api/v1/checkout/{channel}/gratis-rules/{cart_id}/

Response:
{
  "code": "GRATIS300",
  "name": "Gratis Stepped",
  "items": [
    {"sku": "GIFT-001", "price": 0.01},
    {"sku": "GIFT-002", "price": 0.01}
  ],
  "next_gratis_tier_quantity": 2,
  "price_missing_to_next_gratis_tier": 150.00
}

# 2. Select gratis
POST /api/v1/checkout/{channel}/cart/{cart_id}/discounts/
{
  "code": "GRATIS300",
  "sku": "GIFT-001",
  "quantity": 1
}
```

### Test Discount Application

```python
# Apply discount code
POST /api/v1/checkout/{channel}/cart/{cart_id}/discounts/
{
  "code": "SPRING10"
}

# Check cart response includes discount
Response:
{
  "discounts": [
    {
      "code": "SPRING10",
      "status": "valid",
      "modifier": "percent_discount",
      "extra_value": 10
    }
  ]
}
```

## Common Patterns

### Progressive Gratis with Threshold Filter

**Use Case**: "Spend X on category A, get free item from category B"

```yaml
- model: django_checkout.discountrulecode
  fields:
    modifier: gratis_stepped
    extra_value:
      PLN:
        '500': 1

# What counts toward threshold
- model: django_checkout.thresholdproductfilter
  fields:
    is_inclusion_or_exclusion: inclusion
    # M2M: categories = [category_A]

# What user can pick
- model: django_checkout.discountmodeofaction
  fields:
    is_inclusion_or_exclusion: inclusion
    # M2M: categories = [category_B]
```

### Category Sale with Exclusions

**Use Case**: "20% off sofas, except sale items"

```yaml
- model: django_checkout.discountrulecode
  fields:
    modifier: percent_discount
    extra_value: 20

# Include sofas
- model: django_checkout.discountmodeofaction
  pk: 1
  fields:
    is_inclusion_or_exclusion: inclusion
    # M2M: categories = [sofas]

# Exclude sale
- model: django_checkout.discountmodeofaction
  pk: 2
  fields:
    is_inclusion_or_exclusion: exclusion
    # M2M: categories = [sale]
```

### Stacking Discounts

```yaml
# Auto-apply 5% at 1000 PLN
- model: django_checkout.discountrulecode
  pk: 1
  fields:
    name: AUTO_5
    extra_value: 5
    min_order_amount: '1000.00'
    automatic_applications: true
    combine_with_other_rules: true

# Manual 50 PLN off at 500 PLN
- model: django_checkout.discountrulecode
  pk: 2
  fields:
    name: MANUAL_50
    extra_value: 50
    min_order_amount: '500.00'
    combine_with_other_rules: true

# At 1000 PLN cart: Both apply (50 PLN + 5%)
```

## Field Reference

### DiscountRuleCode

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | CharField(128) | - | Internal name |
| `modifier` | CharField | "None" | Discount type (see list above) |
| `extra_value` | JSONField | `{}` | Modifier config (int/dict/list) |
| `target` | CharField | "all" | "all" / "first_order_logged" / "first_order_all" |
| `min_order_amount` | Decimal | 0.00 | Minimum cart value |
| `free_shipping` | Boolean | False | Grant free shipping |
| `free_order` | Boolean | False | Entire order free |
| `is_omnibus` | Boolean | False | Include in omnibus calculations |
| `priority` | SmallInt | null | Lower = higher priority |
| `combine_with_other_rules` | Boolean | False | Can stack with others |
| `automatic_applications` | Boolean | False | Auto-apply without code |
| `is_active` | Boolean | True | Enable/disable |
| `show_when_invalid` | Boolean | True | Show gratis even when unavailable |
| `extension` | JSONField | `{}` | Custom data (marketing copy, etc.) |
| `channels` | M2M | - | Sales channels |
| `currencies` | M2M | - | Currencies (empty = all) |

### DiscountCode

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `code` | CharField | - | User-facing code (e.g., "SPRING10") |
| `max_used` | Integer | 0 | Total use limit (0 = unlimited) |
| `max_uses_per_user` | Integer | 0 | Per-user limit (0 = unlimited) |
| `current_used` | Integer | 0 | Current usage count |
| `active_from` | Date | null | Start date (null = always) |
| `active_to` | Date | null | End date (null = never expires) |
| `max_products_qty` | Integer | null | Max qty per product line |

### AbstractProductFilter (Base for ModeOfAction & ThresholdFilter)

| Field | Type | Description |
|-------|------|-------------|
| `is_inclusion_or_exclusion` | CharField | "inclusion" or "exclusion" |
| `take_common_part` | Boolean | true=AND logic, false=OR logic |
| `categories` | M2M | Product categories |
| `products` | M2M | Specific products (includes children) |
| `attributes` | M2M | Products with attributes |
| `product_price_from/to` | Integer | Unit price range |
| `cart_price_from/to` | Integer | Cart total range |
| `qty_from/to` | Integer | Line qty range |
| `cart_qty_from/to` | Integer | Cart total qty range |

## Troubleshooting

### Discount not applying?

Check:
1. `is_active` = true
2. `min_order_amount` met
3. Cart value >= threshold
4. Code not expired (`active_from` / `active_to`)
5. Usage limits not exceeded
6. Target matches user (first_order_logged requires logged user)
7. If filtered, cart contains matching products

### Gratis not available?

Check:
1. Threshold met (check ThresholdProductFilter if exists)
2. For `gratis_by_sku_in_cart`: all required SKUs in cart
3. `show_when_invalid` setting
4. DiscountModeOfAction defines available products
5. Stock available for gratis products

### User can't select gratis product?

Check:
1. SKU exists in DiscountModeOfAction filter
2. Product is active and in stock
3. Quantity within limits (extension.quantity)

## Documentation Files

- **Full Analysis**: `repos/entirius-tests/docs/DISCOUNT_RULES_ANALYSIS.md`
- **Summary**: `repos/entirius-tests/docs/DISCOUNT_RULES_SUMMARY.md`
- **This File**: `repos/entirius-tests/docs/DISCOUNT_RULES_QUICK_REFERENCE.md`
- **Fixtures**: `repos/entirius-test-package/fixtures/django_checkout.discounts.comprehensive.yaml`
