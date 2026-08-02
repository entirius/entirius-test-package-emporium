#!/bin/bash
#
# seed.sh — Seeds a running Volkanos service with the Emporium test package (host side).
# Prerequisites: a compose stack (e.g. entirius-zeno) with the service, a celery worker,
# and this repo mounted at /entirius/test-package inside the containers.
# Usage: CONTAINER=<service-container> SVC_DIR=<service dir in container> ./scripts/seed.sh
# Defaults target entirius-zeno (make seed wires them up).
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

# ── Progress: every phase goes through step(); the EXIT trap names the phase that failed ──
SEED_START=$SECONDS
SEED_STEP="init"
step() {
    SEED_STEP="$1"
    echo ""
    echo "========================================"
    echo "[$((SECONDS - SEED_START))s] $1"
    echo "========================================"
    echo ""
}
trap 'code=$?; if [ $code -ne 0 ]; then echo ""; echo "SEED FAILED (exit $code) during: $SEED_STEP"; fi' EXIT

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"

# Container/service knobs — the harness (e.g. zeno `make seed`) passes them in.
# Both containers are required explicitly: auto-detecting by name substring can grab
# a container from an unrelated compose project running on the same host.
CONTAINER="${CONTAINER:?CONTAINER not set (service container) - is the stack up? (zeno: make up)}"
DB_CONTAINER="${DB_CONTAINER:?DB_CONTAINER not set (postgres container)}"
SVC_DIR="${SVC_DIR:-/entirius/services/entirius-service-volkanos}"
DB_USER="${DB_USER:-entirius}"
DB_NAME="${DB_NAME:-entirius}"
# Host port of the service — the summary URLs must be clickable from the host.
# Harnesses pass SERVICE_PORT (zeno: 8100); standalone falls back to the container port.
SERVICE_URL="http://localhost:${SERVICE_PORT:-8000}"

echo "Using container: $CONTAINER"

# Check Celery is running
echo "Checking Celery worker..."
CELERY_CHECK=$(docker exec "$CONTAINER" bash -c "celery -A main inspect ping 2>/dev/null | grep -c 'pong'" 2>/dev/null || echo "0")
if [ "$CELERY_CHECK" = "0" ]; then
    echo "ERROR: Celery worker is not running!"
    echo "QMS import requires Celery. Start it before seeding."
    echo ""
    echo "zeno: the worker compose service should be up (make up / make dev); check: docker compose ps worker"
    echo "Manual fallback:"
    echo "  docker exec -d -w $SVC_DIR $CONTAINER celery -A main worker -l info -Q celery,quantities,fill_product_representation,pricemanager_create_pricelist"
    exit 1
fi
echo "Celery is running."

# Check volume mount
echo "Checking test package mount..."
docker exec "$CONTAINER" test -d /entirius/test-package/package || {
    echo "ERROR: /entirius/test-package not mounted in container (zeno: make clone-tests, then restart)."
    exit 1
}

FIXTURES_DIR="/entirius/test-package/fixtures"
PACKAGE_DIR="/entirius/test-package/package"

# Omnibus pipeline — extracted as a function so `seed-fresh` and `seed-omnibus`
# share one implementation. Runs PH backfill → omnibus calc per channel →
# fill read model per shop. Safe to re-run on any DB state.
run_omnibus_pipeline() {
    echo "Backfilling PriceHistory for omnibus demo..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py backfill_demo_price_history 2>&1 | tail -2" || true

    echo "Calculating omnibus prices per channel..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell -c "
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
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell -c "
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
    OMNIBUS_COUNT=$(docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell -c "from django_omnibus.models import OmnibusPrice; print(OmnibusPrice.objects.count())"' 2>/dev/null | tail -1 || echo "?")
    echo ""
    echo "Pipeline status: omnibus calculated for $OMNIBUS_COUNT records"
    exit 0
fi

step "Step 1: Reset + Migrate Database"
echo "Dropping and recreating database..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" > /dev/null 2>&1 || true
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" > /dev/null 2>&1
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";" > /dev/null 2>&1
echo "Database recreated."
echo "Running migrations..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py migrate --noinput"

step "Step 2: Load Fixtures"
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
    # App label comes from the fixture's first `model:` line (filenames are not labels:
    # django_pim_gaps.cfg.yaml holds django_pim models). Skip apps this service does not
    # run (e.g. django_contact_forms ships ahead of its module — spec-first).
    APP=$(grep -m1 -E "^- model:" "$PACKAGE_ROOT/fixtures/$fixture" | sed 's/.*model: *//; s/\..*//')
    if ! docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python -c \"import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','main.settings'); django.setup(); from django.apps import apps; apps.get_app_config('$APP')\"" > /dev/null 2>&1; then
        echo "Skipping $fixture ($APP not installed in this service)"
        continue
    fi
    echo "Loading $fixture..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py loaddata --format=yaml --no-color $FIXTURES_DIR/$fixture"
done

step "Step 3: Create Superuser"
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "DJANGO_SUPERUSER_PASSWORD=admin123 python manage.py createsuperuser --noinput --username admin --email admin@entirius.com 2>/dev/null || echo 'Superuser already exists'"
echo "Creating Customer profile for admin user..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py shell -c \"
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

step "Step 3b: Create Test Users"
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py shell -c \"
from django.contrib.auth import get_user_model
U = get_user_model()
u, created = U.objects.get_or_create(username='testuser', defaults={'email': 'testuser@entirius.com'})
u.set_password('testuser123'); u.is_active = True; u.save()
print('testuser', 'created' if created else 'reset')
\""

step "Step 3c: Suppliers E2E Prep"
# Preset suppliers (incl. "novatrade") + anchor product for the @suppliers scenarios;
# without it the suite depends on suppliers pre-existing in the environment.
if docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python -c \"import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','main.settings'); django.setup(); from django.apps import apps; apps.get_app_config('django_suppliers')\"" > /dev/null 2>&1; then
    docker exec -i -w "$SVC_DIR" "$CONTAINER" python manage.py shell < "$PACKAGE_ROOT/scripts/seed-suppliers-e2e.py"
else
    echo "Skipping suppliers prep (django_suppliers not installed)"
fi

step "Step 4: Import Package Data"
docker exec -e SVC_DIR="$SVC_DIR" "$CONTAINER" bash /entirius/test-package/scripts/import-package.sh "$PACKAGE_DIR"

step "Step 5: Upload ContentDB Images"
docker exec "$CONTAINER" bash /entirius/test-package/scripts/upload-contentdb-images.sh || echo "Image upload skipped (optional)"

step "Step 6: Post-Seed Syncs"
# Sync channels from PIM to dependent modules
echo "Syncing ContentDB languages..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_contentdb_languages 2>/dev/null || true"
echo "Syncing ContentDB channels..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_contentdb_channels 2>/dev/null || true"

# Load agreements module fixtures + sync + publish
echo "Loading agreements fixtures..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py loaddata default_agreements 2>/dev/null || true"
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py loaddata legal_pages 2>/dev/null || true"
echo "Syncing agreement channels..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_agreement_channels 2>/dev/null || true"
echo "Auto-publishing agreement versions..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'DJANGO_SETTINGS_MODULE=main.settings python -c "
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
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py migrate_to_current_price 2>/dev/null || true"

# Omnibus pipeline (PH backfill + calculate + fill read model).
# EU compliance: shows lowest 30-day price during promo. Seed data has
# CurrentPrice with active special_gross_value but zero PriceHistory rows
# (PH is an audit log for real edits, not fixture data) — we synthesize PH
# values so /api/matrix/v2/{ch}/omnibus/?sku= returns meaningful data.
# Re-runnable standalone via `make seed-omnibus`.
run_omnibus_pipeline

# Sync FAQ channels from PIM
echo "Syncing FAQ channels..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_faq_channels --verbosity 0 2>/dev/null || true"

# Sync Deliverypoints channels from PIM
echo "Syncing Deliverypoints channels..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_dp_channels --verbosity 0 2>/dev/null || true"

# Discover Volkanos modules (munin)
echo "Discovering modules..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py discover_modules --verbosity 0 2>/dev/null || true"

# Seed demo enrichment proposals (text + picture) so the CMS review queue has examples to review.
# Runs after the catalogue import — targets the seeded ENT-S00x products via the registered adapter.
echo "Seeding demo enrichment proposals..."
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py seed_demo_proposals --verbosity 0 2>/dev/null || true"

# Backfill QMS Warehouse from authoritative checkout.Stock so the CMS Stock panel
# has data. Warehouse/WarehouseStock is the CMS-facing entry point; further edits
# propagate back to checkout.Stock via signals. XRAY remains the engine for both channels.
echo "Backfilling QMS Warehouse (integration) for each seeded channel..."
for ch in $(docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell --no-imports -c "from django_checkout.models import Channel; print(\" \".join(Channel.objects.values_list(\"idx\", flat=True)))"' 2>/dev/null); do
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py backfill_warehouse --supplier-code=$ch --channel-idx=$ch --warehouse-code=main-$ch 2>&1 | tail -2"
done

# Seed a manual Warehouse per channel so testers can exercise the CMS edit flow
# (manual qty change -> signal -> checkout.Stock -> Matrix re-render) without
# touching the integration warehouses (which are read-only in the UI).
echo "Seeding manual Warehouse per channel (operator-editable)..."
docker cp "$PACKAGE_ROOT/scripts/seed-manual-warehouse.py" "$CONTAINER":/tmp/seed-manual-warehouse.py
docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "DJANGO_SETTINGS_MODULE=main.settings python /tmp/seed-manual-warehouse.py 2>&1 | tail -8"

step "Seed Complete!"
OMNIBUS_COUNT=$(docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell -c "from django_omnibus.models import OmnibusPrice; print(OmnibusPrice.objects.count())"' 2>/dev/null | tail -1 || echo "?")
echo "Pipeline status: omnibus calculated for $OMNIBUS_COUNT records"
echo ""
echo "Admin panel: ${SERVICE_URL}/admin/"
echo "Credentials: admin / admin123"
echo ""
echo "API endpoints (replace {channel} with your configured channel):"
echo "  Matrix:     ${SERVICE_URL}/api/matrix/1/{channel}/products/?language=en&currency=EUR"
echo "  Checkout:   ${SERVICE_URL}/api/checkout/1/{channel}/"
echo "  ContentDB:  ${SERVICE_URL}/api/contentdb/v1/published/static-page/?routes=home&language=EN&access_rights=1"
echo ""
echo "Configured channels (from package):"
if [ -f "$PACKAGE_ROOT/package/volkanos-config/channels.conf" ]; then
    grep -v '^#' "$PACKAGE_ROOT/package/volkanos-config/channels.conf" | grep -v '^$' | while IFS=: read -r ch cur; do
        echo "  $ch ($cur)"
    done
fi
echo ""

echo ""
echo "SEED OK in $((SECONDS - SEED_START))s"
