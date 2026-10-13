#!/bin/bash
#
# import-package.sh — Imports entirius-test-package data into Volkanos
# Runs INSIDE the Docker container
# Usage: ./import-package.sh /entirius/test-package/package
#        SEED_APPS="<labels>" ./import-package.sh --dry-run   (prints the plan; needs nothing else)
#
# Channels are read from volkanos-config/channels.conf inside the package.
# Override via IMPORT_CHANNELS env var (e.g. "default-local:USD,default-europe:EUR").
# Every step runs only when its apps are enabled (guard). The app list is SEED_APPS when
# seed.sh passes it, else one Django boot here. Skips are appended to SEED_SKIP_FILE when set.
#

set -e

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
fi
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

note() { # note <summary line> — printed here, kept for the seed summary
    echo "  $1"
    if [ -n "${SEED_SKIP_FILE:-}" ]; then
        echo "$1" >> "$SEED_SKIP_FILE"
    fi
}
app_installed() { [[ "$APPS" == *" $1 "* ]]; }

# guard <step> [app…] — 0 when every app is enabled (the step starts); otherwise a `skipped:`
# line and 1. With --dry-run it prints the plan line and always returns 1: no step body runs.
guard() {
    local name="$1" app
    shift
    for app in "$@"; do
        app_installed "$app" && continue
        if [ "$DRY_RUN" = "1" ]; then
            echo "seed: plan $name skip ($app not enabled)"
        else
            note "skipped: $name ($app not enabled)"
        fi
        return 1
    done
    if [ "$DRY_RUN" = "1" ]; then
        echo "seed: plan $name run"
        return 1
    fi
    printf '\n========================================\n%s\n========================================\n\n' "$name"
}

if [ "$DRY_RUN" = "1" ]; then
    APPS="${SEED_APPS:?--dry-run needs SEED_APPS (enabled app labels, space- or newline-separated)}"
else
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
    APPS="${SEED_APPS:-}"
    if [ -z "$APPS" ]; then
        APPS=$(python - < "$SCRIPT_DIR/installed-apps.py")
    fi
fi
# shellcheck disable=SC2086 # word splitting on purpose: any whitespace becomes one space
APPS=" $(echo $APPS) "

if guard "import 1 Fixtures"; then
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
                    # References the agreements channel that seed.sh Step 6 syncs from PIM — loaded there.
                    django_agreements.cfg.yaml) echo "  Skipping $(basename "$fixture") (loaded after channel sync)"; continue ;;
                esac
                # A fixture belongs to the app of its first `model:` line (as in seed.sh).
                APP=$(grep -m1 -E "^- model:" "$fixture" | sed 's/.*model: *//; s/\..*//')
                if [ -z "$APP" ]; then
                    echo "ERROR: no '- model:' line in $fixture"
                    exit 1
                fi
                if ! app_installed "$APP"; then
                    note "skipped: import 1 $(basename "$fixture") ($APP not enabled)"
                    continue
                fi
                echo "  Loading $(basename "$fixture")..."
                python manage.py loaddata --format=yaml "$fixture"
            fi
        done
    else
        echo "No fixtures directory found at $FIXTURE_DIR — skipping"
    fi
fi

if guard "import 2 PIM Configuration" django_pim_csv; then
    PIM_CONFIG="$PACKAGE_DIR/volkanos-config"
    python manage.py config-load-pim-channels "$PIM_CONFIG/pim-channels.csv"
    # The CSVs are the source of truth for features, set memberships and positions:
    # any rejected row fails the seed, --prune drops memberships the CSVs do not list.
    python manage.py config-load-pim-features "$PIM_CONFIG/pim-features.csv"
    python manage.py config-load-pim-features-sets "$PIM_CONFIG/pim-features-sets.csv" --prune
    python manage.py config-load-pim-feature-position-in-features-sets "$PIM_CONFIG/pim-feature-position-in-features-sets.csv" --prune

    echo "Checking the PIM config importers reject bad rows (an error below is expected)..."
    out=$(python manage.py config-load-pim-features "$PIM_CONFIG/invalid/pim-features-scope-change.csv" 2>&1 || true)
    if ! grep -q "can not change scope of existing feature series" <<< "$out"; then
        echo "$out"
        echo "ERROR: config-load-pim-features did not reject the scope change of an existing feature"
        exit 1
    fi

    echo "Checking the PIM config CSVs match the database..."
    for check in "features-sets pim-features-sets.csv" "feature-position-in-features-sets pim-feature-position-in-features-sets.csv"; do
        read -r command csv_file <<< "$check"
        out=$(python manage.py "config-load-pim-$command" "$PIM_CONFIG/$csv_file" --prune --dry-run 2>&1) || {
            echo "$out"
            echo "ERROR: dry run of $csv_file failed"
            exit 1
        }
        if ! echo "$out" | grep -q "^Would detach 0 "; then
            echo "$out"
            echo "ERROR: a second import of $csv_file would still detach features"
            exit 1
        fi
    done
fi

if guard "import 3 Attributes" django_pim_csv; then
    python manage.py attributes-import-from-csv badge "$PACKAGE_DIR/attributes--badge.csv"
    python manage.py attributes-import-from-csv brand "$PACKAGE_DIR/attributes--brand.csv"
    python manage.py attributes-import-from-csv series "$PACKAGE_DIR/attributes--series.csv"
    python manage.py attributes-import-from-csv options "$PACKAGE_DIR/attributes--options.csv"
fi

if guard "import 4 Categories" django_pim_csv; then
    for ch in "${CHANNEL_LIST[@]}"; do
        CSV="$PACKAGE_DIR/categories--${ch}.csv"
        if [ -f "$CSV" ]; then
            python manage.py categories-import-from-csv "$ch" "$CSV"
        else
            note "skipped: import 4 Categories ($(basename "$CSV") not in the package)"
        fi
    done
fi

# Read by the product import and by the thumbnails step.
SKIP_PICS="--skip-pictures"
if [ "$DRY_RUN" = "0" ] && [ -d "$(dirname "$PACKAGE_DIR")/images" ]; then
    echo "Images directory found — importing with pictures"
    SKIP_PICS=""
fi

if guard "import 5 Products" django_pim_csv; then
    for ch in "${CHANNEL_LIST[@]}"; do
        CSV="$PACKAGE_DIR/products--${ch}.csv"
        if [ -f "$CSV" ]; then
            python manage.py products-import-from-csv "$ch" "$CSV" $SKIP_PICS
        else
            note "skipped: import 5 Products ($(basename "$CSV") not in the package)"
        fi
    done
fi

if guard "import 6 Product Positions" django_pim_csv; then
    for ch in "${CHANNEL_LIST[@]}"; do
        CSV="$PACKAGE_DIR/products-position--${ch}.csv"
        if [ -f "$CSV" ]; then
            python manage.py products-position-import-from-csv "$ch" "$CSV"
        else
            note "skipped: import 6 Product Positions ($(basename "$CSV") not in the package)"
        fi
    done
fi

if guard "import 7 Prices" django_pricemanager; then
    for ch in "${CHANNEL_LIST[@]}"; do
        CSV="$PACKAGE_DIR/pricelist--${ch}.csv"
        CUR="${CHANNEL_CURRENCY[$ch]}"
        if [ -f "$CSV" ]; then
            python manage.py import-pricelist-from-csv "$ch" "$CSV" --currency_code="$CUR"
        else
            note "skipped: import 7 Prices ($(basename "$CSV") not in the package)"
        fi
    done
    python manage.py manage-pricelists
fi

if guard "import 7b Bundle Component Prices" django_pricemanager django_pim; then
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
fi

if guard "import 7c Thumbnails" django_pim; then
    if [ -z "$SKIP_PICS" ]; then
        echo "Generating thumbnails for imported images..."
        # Soft for one known cause only: a service without THUMBS_CONFIG has no resizer.
        for ch in "${CHANNEL_LIST[@]}"; do
            if out=$(python manage.py pim-thumbs-generate "$ch" 2>&1); then
                echo "$out"
            elif grep -q "THUMBS_CONFIG is not set" <<< "$out"; then
                note "warn: import 7c Thumbnails ($ch: THUMBS_CONFIG is not set in the service settings)"
            else
                echo "$out"
                exit 1
            fi
        done
    else
        note "skipped: import 7c Thumbnails (no images directory in the package)"
    fi
fi

if guard "import 7d Omnibus" django_omnibus; then
    for ch in "${CHANNEL_LIST[@]}"; do
        python manage.py fill-omnibus-product-representation-from-pim "$ch"
    done
    python manage.py calculate-omnibus-price
fi

# Condition-based wait for the async xray pull->push chain (writes checkout.Stock).
# The cap is a safety net, not the expected duration (reaching it fails the import); on a fresh build the chain
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
    echo "ERROR: QMS tasks not complete after ${MAX_WAIT}s"
    return 1
}

# The xray->checkout push that writes checkout.Stock is a downstream async step NOT
# tracked by XrayPointInTime status — a PIT reaches 'done' while configurable-product
# stock is still being written ~30s later (sale/voucher-template SKUs like ENT-S001 land
# LAST, after the simple-product plateau). So PIT-settled is the wrong gate; poll
# checkout.Stock directly and only settle once the non-zero row count has held steady AND
# a minimum drain time has elapsed (the floor defeats the plateau false-positive).
wait_for_checkout_stock() {
    echo "Waiting for checkout.Stock to settle (xray->checkout push)..."
    # Plateau alone false-positives: sale/voucher SKUs (ENT-S001, ENT-C001) land LAST,
    # so additionally require these sentinels to be purchasable before declaring settled.
    local MAX_WAIT=300 MIN_WAIT=45 ELAPSED=10 STABLE=0 PREV=-1 CUR SENT
    sleep 10
    while [ $ELAPSED -lt $MAX_WAIT ]; do
        sleep 5
        ELAPSED=$((ELAPSED + 5))
        CUR=$(python manage.py shell -c "from django_checkout.models import Stock
print(Stock.objects.filter(quantity__gt=0).count())" 2>/dev/null | tail -1)
        SENT=$(python manage.py shell -c "from django_checkout.models import Stock
print(Stock.objects.filter(product__sku__in=['ENT-S001','ENT-C001'], quantity__gt=0).values('product__sku').distinct().count())" 2>/dev/null | tail -1)
        if [ "${CUR:-x}" = "${PREV:-y}" ] && [ "${CUR:-0}" -gt 0 ] 2>/dev/null; then
            STABLE=$((STABLE + 1))
        else
            STABLE=0
        fi
        if [ $STABLE -ge 4 ] && [ $ELAPSED -ge $MIN_WAIT ] && [ "${SENT:-0}" -ge 2 ] 2>/dev/null; then
            echo "checkout.Stock settled at ${CUR} non-zero rows, sentinels present (${ELAPSED}s)"
            return 0
        fi
        echo "  ${ELAPSED}s: ${CUR:-?} non-zero stock rows (stable x${STABLE}, sentinels ${SENT:-0}/2)..."
        PREV="$CUR"
    done
    echo "ERROR: checkout.Stock not settled after ${MAX_WAIT}s"
    return 1
}

if guard "import 8 Quantities" django_qms; then
    python manage.py qms-manage-quantities
    wait_for_qms
fi

if guard "import 9 Matrix" django_matrix; then
    python manage.py fill-read-model
fi

if guard "import 9b Reconcile" django_qms django_checkout django_matrix; then
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
fi

if guard "import 10 Delivery Points" django_deliverypoints; then
    for dp_csv in "$PACKAGE_DIR"/deliverypoints--*.csv; do
        [ -f "$dp_csv" ] || continue
        DP_TYPE=$(basename "$dp_csv" | sed 's/deliverypoints--//;s/\.csv//')
        echo "Importing delivery points: $DP_TYPE"
        python manage.py import_deliverypoints --file "$dp_csv" --type "$DP_TYPE" --mode incremental
    done
fi

if [ "$DRY_RUN" = "0" ]; then
    printf '\n========================================\nImport Complete!\n========================================\n'
    echo "Channels imported: ${CHANNEL_LIST[*]}"
    echo ""
fi
