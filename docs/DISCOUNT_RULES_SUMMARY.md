# Discount Rules Analysis - Executive Summary

## Key Findings

### 1. What is DiscountModeOfAction?

**Model**: `DiscountModeOfAction` (alias: `GratisProductFilter`)
**Location**: `repos/django-apps/django-checkout/src/django_checkout/models/discount_mode_of_actions.py`

**Purpose**:
- **For GRATIS rules**: Defines which products the user can SELECT as gratis
- **For REGULAR discounts**: Defines which products in cart receive the discount

**How it works**:
```python
# Without DiscountModeOfAction:
gratis_stepped → user can pick ANY product as gratis

# With DiscountModeOfAction:
gratis_stepped + ModeOfAction(categories=[ottomans])
  → user can ONLY pick ottomans as gratis
```

**Key Difference from Basic Gratis**:
- `cheapest_gratis` / `most_expensive_gratis` = **Auto-select** from cart (no user choice, no ModeOfAction needed)
- `gratis_stepped` / `gratis_by_sku_in_cart` = **User selects** from available pool (defined by ModeOfAction)

### 2. What is ThresholdProductFilter?

**Model**: `ThresholdProductFilter`
**Location**: Same file as DiscountModeOfAction

**Purpose**: Defines which products COUNT toward the threshold calculation

**Example Use Case**:
```yaml
# Rule: Spend 500 PLN on SOFAS, get FREE OTTOMAN
# Only sofas count toward 500 PLN threshold

ThresholdProductFilter:
  categories: [sofas]      # Only sofas count toward threshold

DiscountModeOfAction:
  categories: [ottomans]   # User picks from ottomans
```

**Real-World Example**:
"Buy 500 PLN worth of electronics, get a free accessory"
- ThresholdProductFilter: electronics category (what counts toward 500 PLN)
- DiscountModeOfAction: accessories category (what user can pick as gratis)

### 3. All Available Discount Rule Types

| Modifier | Description | extra_value Example |
|----------|-------------|---------------------|
| `percent_discount` | Fixed % off | `10` or `{"PLN": 15, "EUR": 10}` |
| `price_discount` | Fixed amount off | `50` or `{"PLN": 100, "EUR": 20}` |
| `step_qty_percent_discount` | % by line qty | `{"1": 5, "3": 10, "5": 15}` |
| `step_qty_percent_discount_whole_cart` | % by cart qty | `{"10": 5, "20": 10}` |
| `step_qty_price_discount_whole_cart` | Price by cart qty | `{"5": 50, "10": 120}` |
| `step_qty_fixed_price_per_currency` | Fixed unit price at qty | `{"PLN": {"2": 89.99, "5": 69.99}}` |
| `step_price_percent_discount` | % by cart value | `{"PLN": {"200": 5, "500": 10}}` |
| `cheapest_gratis` | Auto-select cheapest | `1` (qty) |
| `most_expensive_gratis` | Auto-select most expensive | `1` (qty) |
| `gratis_stepped` | User picks, progressive | `{"PLN": {"300": 1, "600": 2}}` |
| `gratis_by_sku_in_cart` | Conditional gratis | `["SKU1", "SKU2"]` |
| Free shipping | No modifier | `modifier: null, free_shipping: true` |

### 4. Missing Features from Original Fixtures

**We had (10 rules)**:
- ✓ Basic percent/price discounts
- ✓ Auto/cheapest/most expensive gratis
- ✓ One stepped gratis
- ✓ One step price percent
- ✓ Free shipping
- ✓ Auto-apply, combinable, first-order targeting

**We missed**:
- ✗ **ALL quantity-based discounts** (6 variants)
- ✗ **DiscountModeOfAction configuration** (no product filtering)
- ✗ **ThresholdProductFilter** (no selective threshold)
- ✗ **Multi-currency support** (all rules single-currency only)
- ✗ **gratis_by_sku_in_cart** (conditional gratis)
- ✗ **Product filtering** (categories, attributes, price ranges)
- ✗ **Complex filter combinations** (AND/OR logic)
- ✗ **Usage limits** (max_uses, max_uses_per_user)
- ✗ **first_order_all** target

## Gratis Selection UX Flow

### Backend Flow

1. **User cart reaches threshold**
2. **Frontend calls**: `GET /api/v1/checkout/{channel}/gratis-rules/{cart_id}/`
3. **Backend returns**:
   ```json
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
   ```

4. **User selects**: SKU + quantity
5. **Frontend posts**: `POST /api/v1/checkout/{channel}/cart/{cart_id}/discounts/`
   ```json
   {
     "code": "GRATIS300",
     "sku": "GIFT-001",
     "quantity": 1
   }
   ```

6. **Backend validates**:
   - Is gratis rule still valid?
   - Is SKU in allowed pool (DiscountModeOfAction)?
   - Is quantity within limits?

7. **Backend applies**: Gratis item added to cart at GRATIS_PRICE (default 0.01 PLN)

### How DiscountModeOfAction Controls Available Products

```python
# Function: get_all_available_gratis_rules()
# Location: repos/django-apps/django-checkout/src/django_checkout/worker/discount_worker.py:1217

products_eligible_for_gratis = filter_by_inclusion_and_exclusion(
    gratis, cart_body, channel
)
skus_eligible_for_gratis = products_eligible_for_gratis.values_list(
    "real_product__sku", flat=True
)

# Returns list of SKUs user can pick from
# If no DiscountModeOfAction: ALL products
# If DiscountModeOfAction exists: Only filtered products
```

### How ThresholdProductFilter Controls Threshold Calculation

```python
# Function: is_gratis_available()
# Location: Same file, line ~987

if hasattr(discount, "threshold_filters") and discount.threshold_filters.exists():
    filtered_skus = filter_products_by_threshold_filters(discount, cart_data, channel)
    # Recalculate total_price using ONLY filtered products
    total_price = sum(item.total_price for item in cart if item.sku in filtered_skus)
```

## Product Filter Configuration

### AbstractProductFilter Fields

Both DiscountModeOfAction and ThresholdProductFilter extend this:

**Category/Product/Attribute Filters**:
- `categories` (M2M) - Products in these categories
- `products` (M2M) - Specific products (includes children if configurable)
- `attributes` (M2M) - Products with these attributes

**Price Filters**:
- `product_price_from` / `product_price_to` - Unit price range
- `cart_price_from` / `cart_price_to` - Total cart price range

**Quantity Filters**:
- `qty_from` / `qty_to` - Product line quantity range
- `cart_qty_from` / `cart_qty_to` - Total cart quantity range

**Advanced**:
- `features_qty_greater_than_attr_value` - Qty > attribute value
- `features_qty_is_multiple_of_attr_value` - Qty is multiple of attribute

**Logic Control**:
- `is_inclusion_or_exclusion` - "inclusion" or "exclusion"
- `take_common_part` - `true` = AND logic, `false` = OR logic

### Example Configurations

**Simple Category Filter**:
```yaml
- model: django_checkout.discountmodeofaction
  fields:
    rule: <rule_id>
    is_inclusion_or_exclusion: inclusion
    take_common_part: false
    # M2M: categories = ['ottomans']
```

**Price Range Filter**:
```yaml
- model: django_checkout.discountmodeofaction
  fields:
    rule: <rule_id>
    is_inclusion_or_exclusion: inclusion
    product_price_from: 500
    product_price_to: 2000
```

**Exclusion Filter**:
```yaml
- model: django_checkout.discountmodeofaction
  fields:
    rule: <rule_id>
    is_inclusion_or_exclusion: exclusion  # Exclude
    # M2M: categories = ['sale']  # Exclude sale items
```

**Complex (AND logic)**:
```yaml
# Expensive sofas only (category AND price > 1000)
- model: django_checkout.discountmodeofaction
  fields:
    rule: <rule_id>
    is_inclusion_or_exclusion: inclusion
    take_common_part: true  # AND logic
    product_price_from: 1000
    # M2M: categories = ['sofas']
```

## Updated Test Data

**New Fixtures File**: `repos/entirius-test-package/fixtures/django_checkout.discounts.comprehensive.yaml`

**Contains**:
- 32 discount rules (vs original 10)
- All 12 modifier types covered
- DiscountModeOfAction examples
- ThresholdProductFilter examples
- Multi-currency variants
- Filter combinations (AND/OR)
- Usage limit examples

**Important Note**: M2M relationships (categories, products, attributes) need to be set AFTER loaddata via a management command, as YAML fixtures cannot reference by `idx` string.

## Deliverables

1. ✓ **Analysis Document**: `repos/entirius-tests/docs/DISCOUNT_RULES_ANALYSIS.md`
   - Complete model architecture
   - All modifier types explained
   - Gratis system deep dive
   - Product filtering examples
   - Test coverage matrix

2. ✓ **Comprehensive Fixtures**: `repos/entirius-test-package/fixtures/django_checkout.discounts.comprehensive.yaml`
   - 32 discount rules
   - All features covered
   - Ready for import (after M2M setup)

3. ✓ **Summary**: This file

## Next Steps

### 1. Create M2M Setup Script

```python
# repos/entirius-test-package/scripts/setup_discount_filters.py

from django_checkout.models import DiscountModeOfAction, ThresholdProductFilter
from django_pim.models import ProductCategory

# Set category M2M for filter pk=141 (ottomans)
filter141 = DiscountModeOfAction.objects.get(pk=141)
ottoman_category = ProductCategory.objects.get(idx='ottomans')
filter141.categories.add(ottoman_category)

# ... etc for all filters
```

### 2. Expand BDD Feature File

Create comprehensive scenarios for:
- Quantity-based discounts
- Gratis selection flow
- Product filter validation
- Multi-currency handling
- Threshold filter logic
- Edge cases

### 3. Add Step Definitions

```python
# features/steps/discount_steps.py

@when('I request available gratis for my cart')
def step_request_gratis(context):
    response = context.api.get(f'/api/v1/checkout/{context.channel}/gratis-rules/{context.cart_id}/')
    context.response = response

@then('the available gratis products should include "{sku}"')
def step_check_gratis_sku(context, sku):
    items = context.response.json()['items']
    assert any(item['sku'] == sku for item in items)

@when('I select gratis product "{sku}" with quantity {qty:d}')
def step_select_gratis(context, sku, qty):
    data = {
        'code': context.gratis_code,
        'sku': sku,
        'quantity': qty
    }
    response = context.api.post(
        f'/api/v1/checkout/{context.channel}/cart/{context.cart_id}/discounts/',
        json=data
    )
    context.response = response
```

### 4. CSV Metadata

Create `repos/entirius-test-package/package/discounts.csv` documenting all test rules with expected behavior.

### 5. Admin Documentation

Create guide for business users on how to configure discount rules in Django admin, with screenshots and examples for each modifier type.

## Priority Actions

**CRITICAL** (Breaks gratis selection UX):
1. Test gratis with DiscountModeOfAction
2. Test gratis with ThresholdProductFilter
3. Verify gratis selection API endpoints

**HIGH** (Common use cases):
1. Test quantity-based discounts
2. Test multi-currency support
3. Test category-based filtering

**MEDIUM** (Advanced features):
1. Test complex filter combinations
2. Test usage limits
3. Test auto-apply + combinable scenarios

**LOW** (Edge cases):
1. Expired rules with show_when_invalid
2. Out-of-stock gratis handling
3. Extension field usage
