#!/bin/bash
#
# import-package.sh — Imports entirius-test-package data into Volkanos
# Runs INSIDE the Docker container
# Usage: ./import-package.sh /entirius/test-package/package
#
# Channels are read from volkanos-config/channels.conf inside the package.
# Override via IMPORT_CHANNELS env var (e.g. "default-local:USD,default-europe:EUR").
#

set -e

PACKAGE_DIR="${1:?Usage: $0 <package-directory>}"

if [ ! -d "$PACKAGE_DIR" ]; then
    echo "ERROR: Package directory not found: $PACKAGE_DIR"
    exit 1
fi

# ── Load channel configuration ──────────────────────────────────────

CHANNELS_CONF="$PACKAGE_DIR/volkanos-config/channels.conf"
CHANNEL_LIST=()
declare -A CHANNEL_CURRENCY

if [ -n "$IMPORT_CHANNELS" ]; then
    echo "Using channels from IMPORT_CHANNELS env var: $IMPORT_CHANNELS"
    IFS=',' read -ra PAIRS <<< "$IMPORT_CHANNELS"
    for pair in "${PAIRS[@]}"; do
        ch="${pair%%:*}"
        cur="${pair##*:}"
        CHANNEL_LIST+=("$ch")
        CHANNEL_CURRENCY["$ch"]="$cur"
    done
elif [ -f "$CHANNELS_CONF" ]; then
    echo "Reading channels from $CHANNELS_CONF"
    while IFS=: read -r ch cur; do
        [[ "$ch" =~ ^#.*$ || -z "$ch" ]] && continue
        ch=$(echo "$ch" | xargs)
        cur=$(echo "$cur" | xargs)
        CHANNEL_LIST+=("$ch")
        CHANNEL_CURRENCY["$ch"]="$cur"
    done < "$CHANNELS_CONF"
else
    echo "ERROR: No channel configuration found."
    echo "  Create $CHANNELS_CONF or set IMPORT_CHANNELS env var."
    echo "  Format: channel:currency (one per line or comma-separated)"
    exit 1
fi

if [ ${#CHANNEL_LIST[@]} -eq 0 ]; then
    echo "ERROR: No channels configured."
    exit 1
fi

echo "Channels: ${CHANNEL_LIST[*]}"
for ch in "${CHANNEL_LIST[@]}"; do
    echo "  $ch -> ${CHANNEL_CURRENCY[$ch]}"
done

cd "${SVC_DIR:?SVC_DIR not set}"

echo ""
echo "========================================"
echo "Step 1: Fixtures (Django loaddata)"
echo "========================================"
echo ""
FIXTURE_DIR="$(dirname "$PACKAGE_DIR")/fixtures"
if [ -d "$FIXTURE_DIR" ]; then
    echo "Loading Django fixtures from $FIXTURE_DIR..."
    for fixture in "$FIXTURE_DIR"/*.yaml; do
        if [ -f "$fixture" ]; then
            # *_golden* fixtures are unit-test catalogues (own channels at pk 1/2, features at
            # pk 3+) — loading them here would overwrite the real seed records. Skip them.
            # This glob-skip is the canonical guard; the FIXTURE_FILES allow-list in
            # seed.sh is a load-ordering convenience, not a safety boundary.
            case "$(basename "$fixture")" in
                *_golden*) echo "  Skipping $(basename "$fixture") (unit-test fixture)"; continue ;;
            esac
            echo "  Loading $(basename "$fixture")..."
            python manage.py loaddata --format=yaml "$fixture" || echo "WARNING: $(basename "$fixture") failed"
        fi
    done
else
    echo "No fixtures directory found at $FIXTURE_DIR — skipping"
fi

echo ""
echo "========================================"
echo "Step 2: PIM Configuration"
echo "========================================"
echo ""
python manage.py config-load-pim-channels "$PACKAGE_DIR/volkanos-config/pim-channels.csv"
echo "Attempting to load PIM features (may fail — debug on the go)..."
python manage.py config-load-pim-features "$PACKAGE_DIR/volkanos-config/pim-features.csv" || echo "WARNING: config-load-pim-features failed — features loaded from fixture"
python manage.py config-load-pim-features-sets "$PACKAGE_DIR/volkanos-config/pim-features-sets.csv"

if [ -f "$PACKAGE_DIR/volkanos-config/pim-feature-position-in-features-sets.csv" ]; then
    echo "Loading feature positions in feature sets..."
    python manage.py config-load-pim-feature-position-in-features-sets "$PACKAGE_DIR/volkanos-config/pim-feature-position-in-features-sets.csv" || echo "WARNING: config-load-pim-feature-position-in-features-sets failed — positions may use defaults"
fi

echo ""
echo "========================================"
echo "Step 3: Attributes"
echo "========================================"
echo ""
python manage.py attributes-import-from-csv badge "$PACKAGE_DIR/attributes--badge.csv"
python manage.py attributes-import-from-csv brand "$PACKAGE_DIR/attributes--brand.csv"
python manage.py attributes-import-from-csv series "$PACKAGE_DIR/attributes--series.csv"
python manage.py attributes-import-from-csv options "$PACKAGE_DIR/attributes--options.csv"

echo ""
echo "========================================"
echo "Step 4: Categories"
echo "========================================"
echo ""
for ch in "${CHANNEL_LIST[@]}"; do
    CSV="$PACKAGE_DIR/categories--${ch}.csv"
    if [ -f "$CSV" ]; then
        python manage.py categories-import-from-csv "$ch" "$CSV"
    else
        echo "WARNING: $CSV not found — skipping categories for $ch"
    fi
done

echo ""
echo "========================================"
echo "Step 5: Products"
echo "========================================"
echo ""
SKIP_PICS="--skip-pictures"
if [ -d "$(dirname "$PACKAGE_DIR")/images" ]; then
    echo "Images directory found — importing with pictures"
    SKIP_PICS=""
fi
for ch in "${CHANNEL_LIST[@]}"; do
    CSV="$PACKAGE_DIR/products--${ch}.csv"
    if [ -f "$CSV" ]; then
        python manage.py products-import-from-csv "$ch" "$CSV" $SKIP_PICS
    else
        echo "WARNING: $CSV not found — skipping products for $ch"
    fi
done

echo ""
echo "========================================"
echo "Step 6: Product Positions"
echo "========================================"
echo ""
for ch in "${CHANNEL_LIST[@]}"; do
    CSV="$PACKAGE_DIR/products-position--${ch}.csv"
    if [ -f "$CSV" ]; then
        python manage.py products-position-import-from-csv "$ch" "$CSV"
    else
        echo "WARNING: $CSV not found — skipping product positions for $ch"
    fi
done

echo ""
echo "========================================"
echo "Step 7: Prices"
echo "========================================"
echo ""
for ch in "${CHANNEL_LIST[@]}"; do
    CSV="$PACKAGE_DIR/pricelist--${ch}.csv"
    CUR="${CHANNEL_CURRENCY[$ch]}"
    if [ -f "$CSV" ]; then
        python manage.py import-pricelist-from-csv "$ch" "$CSV" --currency_code="$CUR"
    else
        echo "WARNING: $CSV not found — skipping pricelist for $ch"
    fi
done
python manage.py manage-pricelists

echo ""
echo "Step 7b: Bundle Component Prices"
echo ""
python manage.py shell -c "
from django_pricemanager.models import Price, PriceList, ProductRepresentation
from django_pim.models.product_bundle.bundle_link import BundleLink
count = 0
for pricelist in PriceList.objects.all():
    for bl in BundleLink.objects.select_related('product_bundle__real_product', 'subproduct__real_product').all():
        bundle_sku = bl.product_bundle.real_product.sku
        sub_sku = bl.subproduct.real_product.sku
        bundle_pr = ProductRepresentation.objects.filter(sku=bundle_sku).first()
        if not bundle_pr:
            continue
        sub_price = pricelist.prices.filter(product__sku=sub_sku, product_parent__isnull=True, attrs__isnull=True).first()
        if not sub_price:
            continue
        if pricelist.prices.filter(product__sku=sub_sku, product_parent=bundle_pr).exists():
            continue
        Price(
            pricelist=pricelist, product=sub_price.product, product_parent=bundle_pr,
            net_value=sub_price.net_value, gross_value=sub_price.gross_value,
            special_net_value=sub_price.special_net_value, special_gross_value=sub_price.special_gross_value,
            special_from_date=sub_price.special_from_date, special_to_date=sub_price.special_to_date,
            tax_rate=sub_price.tax_rate,
        ).save()
        count += 1
print(f'Created {count} bundle component prices')
"

echo ""
echo "========================================"
echo "Step 7c: Thumbnails"
echo "========================================"
echo ""
if [ -z "$SKIP_PICS" ]; then
    echo "Generating thumbnails for imported images..."
    for ch in "${CHANNEL_LIST[@]}"; do
        python manage.py pim-thumbs-generate "$ch" || echo "WARNING: pim-thumbs-generate $ch failed"
    done
else
    echo "Skipping thumbnail generation (no images imported)"
fi

echo ""
echo "========================================"
echo "Step 7d: Omnibus Prices (EU compliance)"
echo "========================================"
echo ""
for ch in "${CHANNEL_LIST[@]}"; do
    python manage.py fill-omnibus-product-representation-from-pim "$ch"
done
python manage.py calculate-omnibus-price

echo ""
echo "========================================"
echo "Step 8: Quantities (requires Celery)"
echo "========================================"
echo ""
# Condition-based wait for the async xray pull->push chain (writes checkout.Stock).
# The cap is a safety net, not the expected duration; on a fresh build the chain
# routinely exceeds 60s. NOTE: `manage.py shell -c` can emit banner/warning lines on
# stdout before the result, so we take only the LAST line (tail -1) — parsing the whole
# multi-line blob is what silently broke the old loop (it never detected completion and
# always ran to the cap, letting later steps race an incomplete checkout.Stock).
wait_for_qms() {
    echo "Waiting for Celery to process QMS tasks..."
    # Initial settle: qms-manage-quantities dispatches the pull/push chain asynchronously,
    # so give the worker a moment to register the new PITs (move them into waiting/processing)
    # before polling — otherwise the first poll can see only the previous run's 'done' PITs
    # and return immediately.
    sleep 8
    local MAX_WAIT=240 ELAPSED=8 RESULT PIT_TOTAL PIT_PENDING
    while [ $ELAPSED -lt $MAX_WAIT ]; do
        sleep 3
        ELAPSED=$((ELAPSED + 3))
        # A freshly-dispatched PIT starts in 'waiting' (queued), not 'processing' — so
        # is_processing() alone reports "done" the instant after qms-manage-quantities,
        # before the worker even picks the task up. Count BOTH non-terminal states as
        # pending so the wait actually blocks until the xray push has finished writing
        # checkout.Stock; otherwise the next step (or a second push) races incomplete data.
        RESULT=$(python manage.py shell -c "
from django_qms.models import XrayPointInTime
pits = XrayPointInTime.objects.all()
print(f'{pits.count()},{pits.filter(proces_status__in=[\"waiting\",\"processing\"]).count()}')
" 2>/dev/null | tail -1)
        PIT_TOTAL=$(echo "$RESULT" | cut -d, -f1)
        PIT_PENDING=$(echo "$RESULT" | cut -d, -f2)
        if [ "$PIT_TOTAL" -gt 0 ] 2>/dev/null && [ "$PIT_PENDING" -eq 0 ] 2>/dev/null; then
            echo "QMS tasks complete ($PIT_TOTAL PITs settled in ${ELAPSED}s)"
            return 0
        fi
        echo "  ${ELAPSED}s: ${PIT_TOTAL:-0} PITs, ${PIT_PENDING:-?} still pending..."
    done
    echo "WARNING: QMS tasks not complete after ${MAX_WAIT}s — proceeding anyway"
}

# The xray->checkout push that writes checkout.Stock is a downstream async step NOT
# tracked by XrayPointInTime status — a PIT reaches 'done' while configurable-product
# stock is still being written ~30s later (sale/voucher-template SKUs like ENT-S001 land
# LAST, after the simple-product plateau). So PIT-settled is the wrong gate; poll
# checkout.Stock directly and only settle once the non-zero row count has held steady AND
# a minimum drain time has elapsed (the floor defeats the plateau false-positive).
wait_for_checkout_stock() {
    echo "Waiting for checkout.Stock to settle (xray->checkout push)..."
    local MAX_WAIT=180 MIN_WAIT=45 ELAPSED=10 STABLE=0 PREV=-1 CUR
    sleep 10
    while [ $ELAPSED -lt $MAX_WAIT ]; do
        sleep 5
        ELAPSED=$((ELAPSED + 5))
        CUR=$(python manage.py shell -c "from django_checkout.models import Stock
print(Stock.objects.filter(quantity__gt=0).count())" 2>/dev/null | tail -1)
        if [ "${CUR:-x}" = "${PREV:-y}" ] && [ "${CUR:-0}" -gt 0 ] 2>/dev/null; then
            STABLE=$((STABLE + 1))
        else
            STABLE=0
        fi
        if [ $STABLE -ge 4 ] && [ $ELAPSED -ge $MIN_WAIT ]; then
            echo "checkout.Stock settled at ${CUR} non-zero rows (${ELAPSED}s)"
            return 0
        fi
        echo "  ${ELAPSED}s: ${CUR:-?} non-zero stock rows (stable x${STABLE})..."
        PREV="$CUR"
    done
    echo "WARNING: checkout.Stock not settled after ${MAX_WAIT}s — proceeding anyway"
}

python manage.py qms-manage-quantities
wait_for_qms

echo ""
echo "========================================"
echo "Step 9: Matrix (Read Model)"
echo "========================================"
echo ""
python manage.py fill-read-model

echo ""
echo "========================================"
echo "Step 9b: Reconcile quantities (configurable products)"
echo "========================================"
echo ""
# Configurable products (variants with a parent) only have their checkout
# ProductRepresentation rows materialised after the catalogue is fully built, so the
# first quantity push (Step 9) can land on a not-yet-existing representation and leave
# them at stock 0 — sale/voucher-template SKUs like ENT-S001 in particular. Re-push now
# that every representation exists, wait for completion, then rebuild the read model so
# Matrix reflects the reconciled stock. Idempotent: re-pushing the same qty is a no-op
# for products already correct.
python manage.py qms-manage-quantities
wait_for_checkout_stock
python manage.py fill-read-model

echo ""
echo "========================================"
echo "Step 10: Delivery Points"
echo "========================================"
echo ""
for dp_csv in "$PACKAGE_DIR"/deliverypoints--*.csv; do
    [ -f "$dp_csv" ] || continue
    DP_TYPE=$(basename "$dp_csv" | sed 's/deliverypoints--//;s/\.csv//')
    echo "Importing delivery points: $DP_TYPE"
    python manage.py import_deliverypoints --file "$dp_csv" --type "$DP_TYPE" --mode incremental
done

echo ""
echo "========================================"
echo "Import Complete!"
echo "========================================"
echo "Channels imported: ${CHANNEL_LIST[*]}"
echo ""
