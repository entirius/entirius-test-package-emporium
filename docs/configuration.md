# Configuration

Settings of the BDD suite: environment variables, `behave.ini`, channel discovery and reports. The defaults are
those of `features/environment.py` (`before_all`).

## Sources and priority

`behave.ini` is gitignored — copy `behave.ini.example` or generate via
`scripts/generate-behave-ini.sh`. Priority: env vars > `behave.ini` `[behave.userdata]` >
auto-discovery (`discover_channels()` scans `products--{channel}.csv` filenames).

## Key settings

| Key | Env var | Default | Description |
|-----|---------|---------|-------------|
| `api_base_url` | `API_BASE_URL` | `http://localhost:8000` | Backend API URL |
| `api_version` | `API_VERSION` | `1` | API version |
| `test_package_path` | `TEST_PACKAGE_PATH` | `package` | Path to CSV test data |
| `channels` | `CHANNELS` | auto-discover | Comma-separated channel list |
| `primary_channel` | `PRIMARY_CHANNEL` | first channel | Default channel for single-channel tests |
| `admin_username` | `ADMIN_USERNAME` | `admin` | Admin superuser for JWT auth |
| `admin_password` | `ADMIN_PASSWORD` | `admin123` | Admin password |
| `test_username` | `TEST_USERNAME` | `testuser` | Regular (non-admin) user for auth tests |
| `test_password` | `TEST_PASSWORD` | `testuser123` | Regular user password |
| `viewer_username` / `viewer_password` | `VIEWER_USERNAME` / `VIEWER_PASSWORD` | `viewer` / `viewer123` | Access Viewer staff user (`@access`) |
| `editor_username` / `editor_password` | `EDITOR_USERNAME` / `EDITOR_PASSWORD` | `editor` / `editor123` | Access Editor staff user (`@access`) |
| `manager_username` / `manager_password` | `MANAGER_USERNAME` / `MANAGER_PASSWORD` | `manager` / `manager123` | Access Manager staff user (`@access`) |
| `accessadmin_username` / `accessadmin_password` | `ACCESSADMIN_USERNAME` / `ACCESSADMIN_PASSWORD` | `accessadmin` / `accessadmin123` | Access Administrator role, not superuser (`@access-security`) |
| `norole_username` / `norole_password` | `NOROLE_USERNAME` / `NOROLE_PASSWORD` | `norole` / `norole123` | Staff user without a role (`@access-security`) |

Access staff users (seeded only when `django_access` is installed, `ENVIRONMENT=development` only; dev defaults,
never real): `viewer`/`viewer123` (Viewer), `editor`/`editor123` (Editor), `manager`/`manager123` (Manager),
`accessadmin`/`accessadmin123` (Administrator role, not superuser), `norole`/`norole123` (staff without a role) —
staff, not superuser, each with a `Customer` row so the CMS login works (`scripts/seed-access.py`).

Channel auto-discovery scans `test_package_path` for `products--{channel}.csv` filenames.
Point `test_package_path` at any directory with the standard CSV layout to switch datasets.

## End-to-end suites

`make e2e` reads `E2E_BASE_URL` (storefront, default `http://localhost:3100`, set in the Makefile) and `CMS_BASE_URL`
(admin CMS, default `http://localhost:8180`, `src/entirius_tests/cms_e2e.py`); `API_BASE_URL` as above.

## Reports

JUnit XML output goes to `reports/` (gitignored). Used for CI integration.
