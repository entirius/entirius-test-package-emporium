#!/bin/bash
#
# entirius-docker-seed.sh — Seeds Volkanos DB from entirius-docker host
# Prerequisites: entirius-docker running with backend + celery
# Usage: ./scripts/entirius-docker-seed.sh
#

set -e

# Flag parsing — `--omnibus-only` re-runs the omnibus pipeline on an existing DB
# (PH backfill + calculate + fill-read-model). Useful after adding a promo SKU
# fixture without reseeding everything (~5min vs ~30s).
OMNIBUS_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --omnibus-only) OMNIBUS_ONLY=1 ;;
        *) ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"

# Detect container name
CONTAINER=$(docker ps --filter "name=volkanos" --filter "status=running" --format '{{.Names}}' | head -1)
DB_CONTAINER="${DB_CONTAINER:-entirius-docker-db-1}"

if [ -z "$CONTAINER" ]; then
    echo "ERROR: No running volkanos container found."
    echo "Start entirius-docker first: cd entirius-docker && make dev"
    exit 1
fi

echo "Using container: $CONTAINER"

# Check Celery is running
echo "Checking Celery worker..."
CELERY_CHECK=$(docker exec "$CONTAINER" bash -c "celery -A main inspect ping 2>/dev/null | grep -c 'pong'" 2>/dev/null || echo "0")
if [ "$CELERY_CHECK" = "0" ]; then
    echo "ERROR: Celery worker is not running!"
    echo "QMS import requires Celery. Start it before seeding."
    echo ""
    echo "Option 1: If celery service is in docker-compose.yml, restart with 'make dev'"
    echo "Option 2: Run manually:"
    echo "  docker exec -d $CONTAINER bash -c 'cd /entirius/service/$PROJECT_NAME && celery -A main worker -l info -Q celery,quantities,fill_product_representation,pricemanager_create_pricelist &'"
    exit 1
fi
echo "Celery is running."

# Check volume mount
echo "Checking test package mount..."
docker exec "$CONTAINER" test -d /entirius/test-package/package || {
    echo "ERROR: /entirius/test-package not mounted in container."
    echo ""
    echo "Add to docker-compose.dev.yml under volkanos volumes:"
    echo "  - \${TEST_PACKAGE_PATH:-./repos/entirius-test-package}:/entirius/test-package"
    echo ""
    echo "Then restart: make dev"
    exit 1
}

FIXTURES_DIR="/entirius/test-package/fixtures"
PACKAGE_DIR="/entirius/test-package/package"

# Omnibus pipeline — extracted as a function so `seed-fresh` and `seed-omnibus`
# share one implementation. Runs PH backfill → omnibus calc per channel →
# fill read model per shop. Safe to re-run on any DB state.
run_omnibus_pipeline() {
    echo "Backfilling PriceHistory for omnibus demo..."
    docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py backfill_demo_price_history 2>&1 | tail -2" || true

    echo "Calculating omnibus prices per channel..."
    docker exec "$CONTAINER" bash -c 'cd /entirius/service/$PROJECT_NAME && manage.py shell -c "
from django_pricemanager.models import Channel
from django.core.management import call_command
qs = Channel.objects.all()
if not qs.exists():
    print(\"  [WARN] no channels found — pipeline skipped\")
for c in qs:
    print(f\"  - {c.idx}\")
    try:
        call_command(\"calculate-omnibus-price\", channel_idx=c.idx)
    except Exception as exc:
        print(f\"  [WARN] {c.idx} failed: {exc}\")
"'

    echo "Filling matrix omnibus + read model..."
    docker exec "$CONTAINER" bash -c 'cd /entirius/service/$PROJECT_NAME && manage.py shell -c "
from django_pim.models import Shop
from django.core.management import call_command
for s in Shop.objects.all():
    try:
        call_command(\"fill-omnibus-product-representation-from-pim\", s.idx)
        call_command(\"fill-read-model\", channel_idx=s.idx)
    except Exception as exc:
        print(f\"  [WARN] {s.idx} failed: {exc}\")
"'
}

# --omnibus-only short-circuit: skip fixture reload + import; just re-run omnibus.
if [ "$OMNIBUS_ONLY" = "1" ]; then
    echo "========================================"
    echo "Omnibus-only mode (skipping fixture reload)"
    echo "========================================"
    run_omnibus_pipeline
    OMNIBUS_COUNT=$(docker exec "$CONTAINER" bash -c 'cd /entirius/service/$PROJECT_NAME && manage.py shell -c "from django_omnibus.models import OmnibusPrice; print(OmnibusPrice.objects.count())"' 2>/dev/null | tail -1 || echo "?")
    echo ""
    echo "Pipeline status: omnibus calculated for $OMNIBUS_COUNT records"
    exit 0
fi

echo ""
echo "========================================"
echo "Step 1: Reset + Migrate Database"
echo "========================================"
echo ""
echo "Dropping and recreating database..."
docker exec "$DB_CONTAINER" psql -U volkanos -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'volkanos' AND pid <> pg_backend_pid();" > /dev/null 2>&1 || true
docker exec "$DB_CONTAINER" psql -U volkanos -d postgres -c "DROP DATABASE IF EXISTS volkanos;" > /dev/null 2>&1
docker exec "$DB_CONTAINER" psql -U volkanos -d postgres -c "CREATE DATABASE volkanos OWNER volkanos;" > /dev/null 2>&1
echo "Database recreated."
echo "Running migrations..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py migrate --noinput"

echo ""
echo "========================================"
echo "Step 2: Load Fixtures"
echo "========================================"
echo ""
# NOTE: never add *_golden* fixtures here — they are unit-test catalogues reusing real-seed
# pks (channels 1/2). import-package.sh skips them by glob; this list must omit them too.
FIXTURE_FILES=(
    "django_regional.cfg.yaml"
    "django_pim.cfg.yaml"
    "django_pim_gaps.cfg.yaml"
    "django_pim_cascade.cfg.yaml"
    "django_pricemanager.cfg.yaml"
    "django_qms.cfg.yaml"
    "django_checkout.cfg.yaml"
    "django_checkout.discounts.comprehensive.yaml"
    "django_contentdb.cfg.yaml"
    "django_matrix.cfg.yaml"
    "django_accounts.cfg.yaml"
    "django_deliverypoints.cfg.yaml"
    "django_faq.cfg.yaml"
    "django_email.cfg.yaml"
    "django_contact_forms.cfg.yaml"
    "django_enrichment.cfg.yaml"
)

for fixture in "${FIXTURE_FILES[@]}"; do
    echo "Loading $fixture..."
    docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py loaddata --format=yaml --no-color $FIXTURES_DIR/$fixture"
done

echo ""
echo "========================================"
echo "Step 3: Create Superuser"
echo "========================================"
echo ""
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && DJANGO_SUPERUSER_PASSWORD=admin123 manage.py createsuperuser --noinput --username admin --email admin@entirius.com 2>/dev/null || echo 'Superuser already exists'"
echo "Creating Customer profile for admin user..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py shell -c \"
from django.contrib.auth.models import User
from django_accounts.models import Customer
from django_regional.models import Language
from allauth.account.models import EmailAddress
u = User.objects.get(username='admin')
lang = Language.objects.get(iso2__iexact='EN')
c, created = Customer.objects.get_or_create(user=u, defaults={'is_active': True, 'is_verified': True, 'language': lang})
if not created and not c.language:
    c.language = lang
    c.save()
EmailAddress.objects.get_or_create(user=u, email=u.email, defaults={'verified': True, 'primary': True})
print(f'Customer uid={c.uid} created={created}')
\""

echo ""
echo "========================================"
echo "Step 3b: Create Test Users"
echo "========================================"
echo ""
docker exec "$CONTAINER" python /entirius/docker/ensure-test-users.py

echo ""
echo "========================================"
echo "Step 4: Import Package Data"
echo "========================================"
echo ""
docker exec "$CONTAINER" bash -c "chmod +x /entirius/test-package/scripts/import-package.sh && /entirius/test-package/scripts/import-package.sh $PACKAGE_DIR"

echo ""
echo "========================================"
echo "Step 5: Upload ContentDB Images"
echo "========================================"
echo ""
docker exec "$CONTAINER" bash -c "chmod +x /entirius/test-package/scripts/upload-contentdb-images.sh && /entirius/test-package/scripts/upload-contentdb-images.sh" || echo "Image upload skipped (optional)"

echo ""
echo "========================================"
echo "Step 6: Post-Seed Syncs"
echo "========================================"
echo ""
# Sync channels from PIM to dependent modules
echo "Syncing ContentDB languages..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py sync_contentdb_languages 2>/dev/null || true"
echo "Syncing ContentDB channels..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py sync_contentdb_channels 2>/dev/null || true"

# Load agreements module fixtures + sync + publish
echo "Loading agreements fixtures..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py loaddata default_agreements 2>/dev/null || true"
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py loaddata legal_pages 2>/dev/null || true"
echo "Syncing agreement channels..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py sync_agreement_channels 2>/dev/null || true"
echo "Auto-publishing agreement versions..."
docker exec "$CONTAINER" bash -c 'cd /entirius/service/$PROJECT_NAME && DJANGO_SETTINGS_MODULE=main.settings python -c "
import django; django.setup()
try:
    from django_agreements.services import version_service
    from django_agreements.models import AgreementVersion
    published = 0
    for v in AgreementVersion.objects.filter(published_at__isnull=True):
        try:
            version_service.publish_version(pk=v.pk)
            published += 1
        except Exception:
            pass
    print(f\"Published {published} agreement versions\")
except ImportError:
    pass
"'

# Populate CurrentPrice from legacy PriceList snapshots (PM v3 architecture)
echo "Populating CurrentPrice from PriceList snapshots..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py migrate_to_current_price 2>/dev/null || true"

# Omnibus pipeline (PH backfill + calculate + fill read model).
# EU compliance: shows lowest 30-day price during promo. Seed data has
# CurrentPrice with active special_gross_value but zero PriceHistory rows
# (PH is an audit log for real edits, not fixture data) — we synthesize PH
# values so /api/matrix/v2/{ch}/omnibus/?sku= returns meaningful data.
# Re-runnable standalone via `make seed-omnibus`.
run_omnibus_pipeline

# Sync FAQ channels from PIM
echo "Syncing FAQ channels..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py sync_faq_channels --verbosity 0 2>/dev/null || true"

# Sync Deliverypoints channels from PIM
echo "Syncing Deliverypoints channels..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py sync_dp_channels --verbosity 0 2>/dev/null || true"

# Sync voucher channels from PIM (the DB reset above drops the boot-time sync) and
# seed voucher channel config + campaigns + product-vouchers. Idempotent; product
# anchors are resolved by SKU so this MUST run after the package import (Step 4).
echo "Syncing voucher channels..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py sync_voucher_channels 2>/dev/null || true"
echo "Seeding voucher config (channels/campaigns/product-vouchers)..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && DJANGO_SETTINGS_MODULE=main.settings python /entirius/test-package/scripts/seed-vouchers.py 2>&1 | tail -12" || echo "Voucher seed skipped (module absent?)"

# Discover Volkanos modules (munin)
echo "Discovering modules..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py discover_modules --verbosity 0 2>/dev/null || true"

# Seed demo enrichment proposals (text + picture) so the CMS review queue has examples to review.
# Runs after the catalogue import — targets the seeded ENT-S00x products via the registered adapter.
echo "Seeding demo enrichment proposals..."
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py seed_demo_proposals --verbosity 0 2>/dev/null || true"

# Backfill QMS Warehouse from authoritative checkout.Stock so the CMS Stock panel
# has data. Warehouse/WarehouseStock is the CMS-facing entry point; further edits
# propagate back to checkout.Stock via signals. XRAY remains the engine for both channels.
echo "Backfilling QMS Warehouse (integration) for each seeded channel..."
for ch in $(docker exec "$CONTAINER" bash -c 'cd /entirius/service/$PROJECT_NAME && manage.py shell --no-imports -c "from django_checkout.models import Channel; print(\" \".join(Channel.objects.values_list(\"idx\", flat=True)))"' 2>/dev/null); do
    docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && manage.py backfill_warehouse --supplier-code=$ch --channel-idx=$ch --warehouse-code=main-$ch 2>&1 | tail -2"
done

# Seed a manual Warehouse per channel so testers can exercise the CMS edit flow
# (manual qty change -> signal -> checkout.Stock -> Matrix re-render) without
# touching the integration warehouses (which are read-only in the UI).
echo "Seeding manual Warehouse per channel (operator-editable)..."
docker cp "$PACKAGE_ROOT/scripts/seed-manual-warehouse.py" "$CONTAINER":/tmp/seed-manual-warehouse.py
docker exec "$CONTAINER" bash -c "cd /entirius/service/\$PROJECT_NAME && DJANGO_SETTINGS_MODULE=main.settings python /tmp/seed-manual-warehouse.py 2>&1 | tail -8"

echo ""
echo "========================================"
echo "Seed Complete!"
echo "========================================"
echo ""
OMNIBUS_COUNT=$(docker exec "$CONTAINER" bash -c 'cd /entirius/service/$PROJECT_NAME && manage.py shell -c "from django_omnibus.models import OmnibusPrice; print(OmnibusPrice.objects.count())"' 2>/dev/null | tail -1 || echo "?")
echo "Pipeline status: omnibus calculated for $OMNIBUS_COUNT records"
echo ""
echo "Admin panel: http://localhost:8000/admin/"
echo "Credentials: admin / admin123"
echo ""
echo "API endpoints (replace {channel} with your configured channel):"
echo "  Matrix:     http://localhost:8000/api/matrix/1/{channel}/products/?language=en&currency=EUR"
echo "  Checkout:   http://localhost:8000/api/checkout/1/{channel}/"
echo "  ContentDB:  http://localhost:8000/api/contentdb/v1/published/static-page/?routes=home&language=EN&access_rights=1"
echo ""
echo "Configured channels (from package):"
if [ -f "$PACKAGE_ROOT/package/volkanos-config/channels.conf" ]; then
    grep -v '^#' "$PACKAGE_ROOT/package/volkanos-config/channels.conf" | grep -v '^$' | while IFS=: read -r ch cur; do
        echo "  $ch ($cur)"
    done
fi
echo ""
