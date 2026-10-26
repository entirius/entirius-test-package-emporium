#!/bin/bash
#
# seed.sh — Seeds a running Volkanos service with the Emporium test package (host side).
# Prerequisites: a compose stack (e.g. entirius-zeno) with the service, a celery worker,
# and this repo mounted at /entirius/test-package inside the containers.
# Usage: CONTAINER=<service-container> SVC_DIR=<service dir in container> ./scripts/seed.sh
# Defaults target entirius-zeno (make seed wires them up).
# The seed follows the enabled apps: every module-specific step runs only when its apps are
# enabled (guard), and the summary names what was skipped.
#   SEED_PROFILE=full            the only profile: every data set whose apps are enabled
#   SEED_APPS="<labels>" ./scripts/seed.sh --dry-run
#                                prints the plan (run / skip per step) for that app list;
#                                no docker, no database
#

set -e

# Flag parsing — `--omnibus-only` re-runs the omnibus pipeline on an existing DB
# (PH backfill + calculate + fill-read-model). Useful after adding a promo SKU
# fixture without reseeding everything (~5min vs ~30s).
OMNIBUS_ONLY=0
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --omnibus-only) OMNIBUS_ONLY=1 ;;
        --dry-run) DRY_RUN=1 ;;
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

# ── Summary: a skip or a warning is printed where it happens and again before the last line ──
NOTES=()
note() { # note <skipped|warn> <step> <reason>
    NOTES+=("$1: $2 ($3)")
    echo "  $1: $2 ($3)"
}
count_notes() { printf '%s\n' "${NOTES[@]}" | grep -c "^$1: " || true; }

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
            note skipped "$name" "$app not enabled"
        fi
        return 1
    done
    if [ "$DRY_RUN" = "1" ]; then
        echo "seed: plan $name run"
        return 1
    fi
    step "$name"
}

# Module presence alone selects the data sets, so one profile covers every module subset.
SEED_PROFILE="${SEED_PROFILE:-full}"
if [ "$SEED_PROFILE" != "full" ]; then
    echo "unknown SEED_PROFILE '$SEED_PROFILE' (known: full)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"

# Container/service knobs — the harness (e.g. zeno `make seed`) passes them in.
# Both containers are required explicitly: auto-detecting by name substring can grab
# a container from an unrelated compose project running on the same host.
if [ "$DRY_RUN" = "0" ]; then
    CONTAINER="${CONTAINER:?not set - pass CONTAINER=<service container name> (zeno: make up + make seed does this)}"
    DB_CONTAINER="${DB_CONTAINER:?DB_CONTAINER not set (postgres container)}"
fi
SVC_DIR="${SVC_DIR:-/entirius/services/entirius-service-volkanos}"
DB_USER="${DB_USER:-entirius}"
DB_NAME="${DB_NAME:-entirius}"
# Host port of the service — the summary URLs must be clickable from the host.
# Harnesses pass SERVICE_PORT (zeno: 8100); standalone falls back to the container port.
SERVICE_URL="http://localhost:${SERVICE_PORT:-8000}"

preflight() {
    echo "Using container: $CONTAINER"

    # Check Celery is running. A dev-mode worker re-syncs its venv before starting
    # celery (first run takes minutes), so poll instead of a single-shot ping —
    # `make dev && make seed` must not race the worker's first boot.
    echo "Checking Celery worker (waits up to ${CELERY_WAIT:-300}s for a dev worker's first venv sync)..."
    CELERY_DEADLINE=$(( $(date +%s) + ${CELERY_WAIT:-300} ))
    while true; do
        CELERY_CHECK=$(docker exec "$CONTAINER" bash -c "celery -A main inspect ping 2>/dev/null | grep -c 'pong'" 2>/dev/null || echo "0")
        [ "$CELERY_CHECK" != "0" ] && break
        if [ "$(date +%s)" -ge "$CELERY_DEADLINE" ]; then
            echo "ERROR: Celery worker is not running!"
            echo "QMS import requires Celery. Start it before seeding."
            echo ""
            echo "zeno: the worker compose service should be up (make up / make dev); check: docker compose ps worker"
            echo "Manual fallback:"
            echo "  docker exec -d -w $SVC_DIR $CONTAINER celery -A main worker -l info -Q celery,quantities,fill_product_representation,pricemanager_create_pricelist"
            exit 1
        fi
        echo "  ... celery not answering yet, retrying"
        sleep 5
    done
    echo "Celery is running."

    # Check volume mount
    echo "Checking test package mount..."
    docker exec "$CONTAINER" test -d /entirius/test-package/package || {
        echo "ERROR: /entirius/test-package not mounted in container (zeno: make clone-tests, then restart)."
        exit 1
    }
}

FIXTURES_DIR="/entirius/test-package/fixtures"
PACKAGE_DIR="/entirius/test-package/package"

# One app list per run: a single Django boot, reused by every guard. A boot error ends the
# seed here (during: init) — a service that does not start is never read as "module absent".
if [ "$DRY_RUN" = "1" ]; then
    APPS="${SEED_APPS:?--dry-run needs SEED_APPS (enabled app labels, space- or newline-separated)}"
else
    preflight
    APPS=$(docker exec -i -w "$SVC_DIR" "$CONTAINER" python - < "$PACKAGE_ROOT/scripts/installed-apps.py")
fi
# shellcheck disable=SC2086 # word splitting on purpose: any whitespace becomes one space
APPS=" $(echo $APPS) "
app_installed() { [[ "$APPS" == *" $1 "* ]]; }
if [ "$DRY_RUN" = "0" ]; then
    echo "Enabled apps: $(wc -w <<< "$APPS")"
fi

# Omnibus pipeline — extracted as a function so `seed-fresh` and `seed-omnibus`
# share one implementation. Runs PH backfill → omnibus calc per channel →
# fill read model per shop. Safe to re-run on any DB state. A failing channel fails the seed.
run_omnibus_pipeline() {
    echo "Backfilling PriceHistory for omnibus demo..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py backfill_demo_price_history"

    echo "Calculating omnibus prices per channel..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell -c "
from django_pricemanager.models import Channel
from django.core.management import call_command
qs = Channel.objects.all()
if not qs.exists():
    print(\"  [WARN] no channels found — pipeline skipped\")
for c in qs:
    print(f\"  - {c.idx}\")
    call_command(\"calculate-omnibus-price\", channel_idx=c.idx)
"'

    echo "Filling matrix omnibus + read model..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell -c "
from django_pim.models import Shop
from django.core.management import call_command
for s in Shop.objects.all():
    call_command(\"fill-omnibus-product-representation-from-pim\", s.idx)
    call_command(\"fill-read-model\", channel_idx=s.idx)
"'
}

omnibus_count() {
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell -c "from django_omnibus.models import OmnibusPrice; print(OmnibusPrice.objects.count())"' 2>/dev/null | tail -1
}
OMNIBUS_APPS="django_omnibus django_pricemanager django_pim django_matrix"

# --omnibus-only short-circuit: skip fixture reload + import; just re-run omnibus.
if [ "$OMNIBUS_ONLY" = "1" ]; then
    # shellcheck disable=SC2086 # one guard argument per app
    if guard "Omnibus-only mode (skipping fixture reload)" $OMNIBUS_APPS; then
        run_omnibus_pipeline
        echo ""
        echo "Pipeline status: omnibus calculated for $(omnibus_count) records"
    fi
    exit 0
fi

if guard "Step 1: Reset + Migrate Database"; then
    echo "Dropping and recreating database..."
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" > /dev/null
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" > /dev/null 2>&1
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";" > /dev/null 2>&1
    echo "Database recreated."
    echo "Running migrations..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py migrate --noinput"
    # The DB is fresh but Redis is not — DRF throttle counters (e.g. pricefighter apply,
    # 30/hour per user) and other cached state would leak into the new environment and
    # 429 the BDD suite on repeated seed+bdd cycles.
    echo "Clearing Django cache (throttle counters, cached state)..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py shell -c \"from django.core.cache import cache; cache.clear(); print('cache cleared')\""
fi

# The communicator daily send counters live in plain Redis (not the Django cache) — the
# @communicator-oneshot cap scenario needs them empty on a fresh seed.
if guard "Step 1: Communicator Counters" django_communicator; then
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py shell -c \"import redis; from django_communicator import settings as s; r = redis.Redis.from_url(s.COMMUNICATOR_REDIS_URL); print('communicator counters cleared:', sum(r.delete(k) for k in r.scan_iter('communicator:sent:*')))\""
fi

# Harnesses with a mail sandbox (zeno: GreenMail) pass its REST URL — scenarios start from an
# empty mailbox. The sandbox is not part of the service: no URL is a skip, no answer a warning.
if guard "Step 1: Mail Sandbox Purge"; then
    if [ -z "${GREENMAIL_API_URL:-}" ]; then
        note skipped "Step 1: Mail Sandbox Purge" "GREENMAIL_API_URL not set"
    elif curl -fsS --max-time 10 -X POST "$GREENMAIL_API_URL/api/mail/purge" > /dev/null; then
        echo "GreenMail purged."
    else
        note warn "Step 1: Mail Sandbox Purge" "no answer at $GREENMAIL_API_URL, mailbox scenarios may see stale mail"
    fi
fi

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
    "django_communicator.cfg.yaml"
    "django_leads.cfg.yaml"
    "django_leads_retention.cfg.yaml"
    "django_enrichment.cfg.yaml"
    "django_notifications.cfg.yaml"
    "django_siteintel.cfg.yaml"
)

if guard "Step 2: Load Fixtures"; then
    for fixture in "${FIXTURE_FILES[@]}"; do
        # App label comes from the fixture's first `model:` line (filenames are not labels:
        # django_pim_gaps.cfg.yaml holds django_pim models). A fixture of an app this service
        # does not run is skipped.
        APP=$(grep -m1 -E "^- model:" "$PACKAGE_ROOT/fixtures/$fixture" | sed 's/.*model: *//; s/\..*//')
        if [ -z "$APP" ]; then
            echo "ERROR: no '- model:' line in fixtures/$fixture"
            exit 1
        fi
        if ! app_installed "$APP"; then
            note skipped "Step 2: $fixture" "$APP not enabled"
            continue
        fi
        echo "Loading $fixture..."
        docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py loaddata --format=yaml --no-color $FIXTURES_DIR/$fixture"
    done
fi

if guard "Step 3: Create Superuser"; then
    if out=$(docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "DJANGO_SUPERUSER_PASSWORD=admin123 python manage.py createsuperuser --noinput --username admin --email admin@entirius.com" 2>&1); then
        echo "$out"
    elif grep -q "already taken" <<< "$out"; then
        note skipped "Step 3: Create Superuser" "admin already exists"
    else
        echo "$out"
        exit 1
    fi
fi

if guard "Step 3: Admin Customer Profile" django_accounts; then
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
fi

if guard "Step 3b: Create Test Users"; then
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py shell -c \"
from django.contrib.auth import get_user_model
U = get_user_model()
u, created = U.objects.get_or_create(username='testuser', defaults={'email': 'testuser@entirius.com'})
u.set_password('testuser123'); u.is_active = True; u.save()
print('testuser', 'created' if created else 'reset')
\""
fi

if guard "Step 3c: Suppliers E2E Prep" django_suppliers; then
    # Preset suppliers (incl. "novatrade") + anchor product for the @suppliers scenarios;
    # without it the suite depends on suppliers pre-existing in the environment.
    docker exec -i -w "$SVC_DIR" "$CONTAINER" python manage.py shell < "$PACKAGE_ROOT/scripts/seed-suppliers-e2e.py"
fi

if guard "Step 3d: Atlas E2E Prep" django_atlas; then
    # EAN anchors, duplicate RealProduct pairs, atlas sources (nova/push/watchers) +
    # warehouse — everything Step 6x and the @atlas BDD suite address by natural key.
    docker exec -i -w "$SVC_DIR" "$CONTAINER" python manage.py shell < "$PACKAGE_ROOT/scripts/seed-atlas-e2e.py"
fi

if guard "Step 3e: Access Staff Users" django_access; then
    # viewer/editor/manager/accessadmin (built-in roles) + norole — staff, not superuser; refuses outside development.
    docker exec -i -w "$SVC_DIR" "$CONTAINER" python manage.py shell < "$PACKAGE_ROOT/scripts/seed-access.py"
fi

# import-package.sh guards its own steps with the same app list; the skips it records come
# back through SEED_SKIP_FILE (a file in the container) and join the summary.
SKIP_FILE="/tmp/seed-skipped-$$"
if guard "Step 4: Import Package Data"; then
    docker exec -e SVC_DIR="$SVC_DIR" -e SEED_APPS="$APPS" -e SEED_SKIP_FILE="$SKIP_FILE" "$CONTAINER" bash /entirius/test-package/scripts/import-package.sh "$PACKAGE_DIR"
    mapfile -t IMPORT_NOTES < <(docker exec "$CONTAINER" bash -c "cat $SKIP_FILE 2>/dev/null; rm -f $SKIP_FILE")
    NOTES+=("${IMPORT_NOTES[@]}")
fi
if [ "$DRY_RUN" = "1" ]; then
    SEED_APPS="$APPS" bash "$SCRIPT_DIR/import-package.sh" --dry-run
fi

if guard "Step 4b: Access Legacy Keys" django_access; then
    # Every fixture key (loaded above) becomes a legacy token; --check fails the seed on a key the import missed.
    docker exec -w "$SVC_DIR" "$CONTAINER" python manage.py access_import_legacy_keys --report
    docker exec -w "$SVC_DIR" "$CONTAINER" python manage.py access_import_legacy_keys --check
fi

if guard "Step 5: Upload ContentDB Images" django_contentdb; then
    if compgen -G "$PACKAGE_ROOT/images/*.png" > /dev/null; then
        docker exec "$CONTAINER" bash /entirius/test-package/scripts/upload-contentdb-images.sh
    else
        note skipped "Step 5: Upload ContentDB Images" "no images/*.png in the package"
    fi
fi

# Step 6: post-seed syncs — one guard per module, channels are synced from PIM to each of them.
if guard "Step 6: ContentDB Syncs" django_contentdb; then
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_contentdb_languages"
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_contentdb_channels"
fi

# Accounts keep their own product list (SKU + name per channel) for wishlists; while it is empty every wishlist
# add answers 400 "No SKUs in accounts product representation". Filled from each PIM shop whose idx is an
# accounts channel; re-runnable (existing SKUs are updated). One call per channel: a single call without
# --pim_shop_idx carries the first shop's products into the next channel (accounts 5.0.0 never resets its list).
if guard "Step 6: Accounts Product Representation" django_accounts django_pim; then
    ACCOUNTS_CHANNELS=$(docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell --no-imports -c "from django_accounts.models import Channel; print(\" \".join(Channel.objects.values_list(\"idx\", flat=True)))"')
    for ch in $ACCOUNTS_CHANNELS; do
        docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py fill-accounts-product-representation-from-pim --pim_shop_idx $ch"
    done
fi

# Agreements module fixtures + sync + clause sets + publish
if guard "Step 6: Agreements" django_agreements; then
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py loaddata default_agreements"
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py loaddata legal_pages"
    echo "Syncing agreement channels..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_agreement_channels"
    echo "Loading agreement clause sets..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py loaddata --format=yaml --no-color $FIXTURES_DIR/django_agreements.cfg.yaml"
    # Language has no natural key — fail loudly when language pks 1/2 are not pl/en
    docker exec -w "$SVC_DIR" "$CONTAINER" python manage.py shell -c '
from django_agreements.models import ClauseSet
got = {(c.pk, c.channel.idx, c.language.iso2) for c in ClauseSet.objects.filter(pk__lte=4)}
expected = {(1, "default-europe", "pl"), (2, "default-europe", "en"), (3, "default-europe", "pl"), (4, "default-europe", "en")}
assert got == expected, f"agreement clause sets attached wrong: {sorted(got)}"
print("Agreement clause sets OK")
'
    echo "Auto-publishing agreement versions..."
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'DJANGO_SETTINGS_MODULE=main.settings python -c "
import django; django.setup()
from django_agreements.services import version_service
from django_agreements.models import AgreementVersion
versions = list(AgreementVersion.objects.filter(published_at__isnull=True))
for v in versions:
    version_service.publish_version(pk=v.pk)
print(f\"Published {len(versions)} agreement versions\")
"'
fi

# Populate CurrentPrice from legacy PriceList snapshots (PM v3 architecture)
if guard "Step 6: CurrentPrice Migration" django_pricemanager; then
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py migrate_to_current_price"
fi

# Omnibus pipeline (PH backfill + calculate + fill read model).
# EU compliance: shows lowest 30-day price during promo. Seed data has
# CurrentPrice with active special_gross_value but zero PriceHistory rows
# (PH is an audit log for real edits, not fixture data) — we synthesize PH
# values so /api/matrix/v2/{ch}/omnibus/?sku= returns meaningful data.
# Re-runnable standalone via `make seed-omnibus`.
# shellcheck disable=SC2086 # one guard argument per app
if guard "Step 6: Omnibus Pipeline" $OMNIBUS_APPS; then
    run_omnibus_pipeline
fi

if guard "Step 6: FAQ Channel Sync" django_faq; then
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_faq_channels --verbosity 0"
fi

if guard "Step 6: Delivery Points Channel Sync" django_deliverypoints; then
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_dp_channels --verbosity 0"
fi

# Discover Volkanos modules (munin). The leads platform modules this service enables must be
# registered: a missing one silently skips its BDD features later.
if guard "Step 6: Module Registry" django_munin; then
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py discover_modules --verbosity 0"
    EXPECTED_MODULES=""
    for key in leads communicator siteintel notifications; do
        if app_installed "django_$key"; then EXPECTED_MODULES="$EXPECTED_MODULES $key"; fi
    done
    echo "Checking leads platform modules in the registry:${EXPECTED_MODULES:- none enabled}"
    docker exec -e EXPECTED_MODULES="$EXPECTED_MODULES" -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py shell --no-imports -c \"
import os
from django_munin.models import Module
expected = set(os.environ['EXPECTED_MODULES'].split())
missing = expected - set(Module.objects.filter(key__in=expected).values_list('key', flat=True))
if missing:
    raise SystemExit('ERROR: munin registry is missing modules: ' + ', '.join(sorted(missing)))
print('Registry lists', Module.objects.filter(key__in=expected).count(), 'of', len(expected), 'leads platform modules.')
\""
fi

# Seed demo enrichment proposals (text + picture) so the CMS review queue has examples to review.
# Runs after the catalogue import — targets the seeded ENT-S00x products via the registered adapter.
# Soft for one known cause only: a service whose ENRICHMENT_ADAPTERS setting does not register
# the adapter of the demo proposals' target module cannot take them in.
if guard "Step 6: Demo Enrichment Proposals" django_enrichment; then
    if out=$(docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py seed_demo_proposals --verbosity 0" 2>&1); then
        echo "$out"
    elif grep -q "no enrichment adapter for target_module" <<< "$out"; then
        note warn "Step 6: Demo Enrichment Proposals" "ENRICHMENT_ADAPTERS in the service settings lacks the adapter of the demo proposals"
    else
        echo "$out"
        exit 1
    fi
fi

# Backfill QMS Warehouse from authoritative checkout.Stock so the CMS Stock panel
# has data. Warehouse/WarehouseStock is the CMS-facing entry point; further edits
# propagate back to checkout.Stock via signals. XRAY remains the engine for both channels.
if guard "Step 6: Warehouse Backfill" django_checkout django_qms; then
    echo "Backfilling QMS Warehouse (integration) for each seeded channel..."
    WAREHOUSE_CHANNELS=$(docker exec -w "$SVC_DIR" "$CONTAINER" bash -c 'python manage.py shell --no-imports -c "from django_checkout.models import Channel; print(\" \".join(Channel.objects.values_list(\"idx\", flat=True)))"')
    for ch in $WAREHOUSE_CHANNELS; do
        docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py backfill_warehouse --supplier-code=$ch --channel-idx=$ch --warehouse-code=main-$ch"
    done

    # Seed a manual Warehouse per channel so testers can exercise the CMS edit flow
    # (manual qty change -> signal -> checkout.Stock -> Matrix re-render) without
    # touching the integration warehouses (which are read-only in the UI).
    echo "Seeding manual Warehouse per channel (operator-editable)..."
    docker cp "$PACKAGE_ROOT/scripts/seed-manual-warehouse.py" "$CONTAINER":/tmp/seed-manual-warehouse.py
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "DJANGO_SETTINGS_MODULE=main.settings python /tmp/seed-manual-warehouse.py"
fi

# Real import through the xml_feed connector (fixtures container over HTTP), then
# the workload script shapes the operator queues: approve+push (auto-match, tolerance
# violation), queued for Swipe, rejected, Updated-tab bump, monitoring observations.
if guard "Step 6x: Atlas Pipeline" django_atlas; then
    docker exec -w "$SVC_DIR" "$CONTAINER" python manage.py execute_source_feed --source-idx atl-nova --feed-idx main --mode full
    docker exec -i -w "$SVC_DIR" "$CONTAINER" python manage.py shell < "$PACKAGE_ROOT/scripts/seed-atlas-workload.py"
fi

# Loads fixtures/lookup/{pim_products,atlas_products}.json (pair-class design in
# scripts/generate-lookup-fixtures.py), attaches pictures from the in-network `fixtures` host,
# backfills fingerprints (+ images when `embed` answers) and seeds one pending duplicate-in-pim
# proposal for the @lookup-oneshot accept scenario. After atlas (needs atl-lookup-* to be free
# source idxs and the `default-europe` channel from Step 4) and before pricefighter (unrelated,
# disjoint SKU/idx sets — order between the two does not matter functionally).
if guard "Step 6z: Lookup Calibration Prep" django_lookup django_atlas; then
    docker exec -i -w "$SVC_DIR" "$CONTAINER" python manage.py shell < "$PACKAGE_ROOT/scripts/seed-lookup.py"
fi

# Channel + representation sync from PIM, then the workload script: pricemanager
# costs/baseline/bounds, quote configs, pricing rules, observations covering every
# recommendation type, and a couple of real applies for the History panel.
# Both apps required: the pricefighter seed hard-imports django_atlas (observations)
# and reads the atl-watch-* sources created by Step 3d.
if guard "Step 6y: PriceFighter Prep" django_pricefighter django_atlas; then
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py sync_pricefighter_channels"
    docker exec -w "$SVC_DIR" "$CONTAINER" bash -c "python manage.py pricefighter_full_sync"
    docker exec -i -w "$SVC_DIR" "$CONTAINER" python manage.py shell < "$PACKAGE_ROOT/scripts/seed-pricefighter-e2e.py"
fi

if [ "$DRY_RUN" = "1" ]; then
    exit 0
fi

step "Seed Complete!"
if app_installed django_omnibus; then
    echo "Pipeline status: omnibus calculated for $(omnibus_count) records"
fi
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
for line in "${NOTES[@]}"; do
    echo "  $line"
done
echo "SEED OK in $((SECONDS - SEED_START))s (profile $SEED_PROFILE, $(count_notes skipped) skipped, $(count_notes warn) warnings)"
