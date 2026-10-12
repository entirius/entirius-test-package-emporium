# Seed and harness

How the package is seeded and run inside the entirius-zeno harness (https://github.com/entirius/entirius-zeno).
None of the `make` targets on this page belongs to this repository's Makefile.

## Harness targets

In the entirius-zeno harness:

- `make clone-tests` clones this package next to the stack; `make seed` runs `scripts/seed.sh` against the stack's
  database; `make bdd [TAGS=@tag]` runs the behave suite; `make e2e` runs the Playwright suites.
- `make mail` starts the GreenMail sandbox the mail steps and `@harness` need.
- The harness passes `GREENMAIL_API_URL` to the seed: `seed.sh` purges GreenMail once when it is set (a `skipped:`
  line without it, a `warn:` line when the sandbox does not answer).
- `scripts/secret_scan.py --fixtures fixtures` reads text on stdin (service and worker logs, a Redis key list) and
  counts access tokens and legacy fixture keys in it, never printing a match; exit 1 on any.

## One-shot scenarios

`@lookup-oneshot`, `@leads-oneshot` (incl. the `@funnel` feature), `@communicator-oneshot` and `@toolbox-oneshot`
(`@toolbox-down`, simulated toolbox outage), plus the suppliers audit-trail and atlas push/merge scenarios, mutate a
specific pre-seeded row once per database — re-running them against an already-consumed database fails on purpose.
A BDD re-run needs a fresh seed (in the entirius-zeno harness: `make seed`).

## Module subsets

The seed and the suite follow the modules the service enables. `scripts/seed.sh` reads the enabled apps once
(`scripts/installed-apps.py`; a service that does not boot fails the seed at `init`) and wraps every step in
`guard <step> [app…]`, as does `scripts/import-package.sh`: a step whose apps are not all enabled prints
`skipped: <step> (<app> not enabled)`, a step that applies is fatal, and the last line reads `SEED OK in <N>s (profile
full, <S> skipped, <W> warnings)` after one line per skip and warning. `SEED_PROFILE` has one value, `full` (every data
set whose apps are enabled); anything else fails at `init`. `SEED_APPS="<labels>" scripts/seed.sh --dry-run` prints
the plan (`seed: plan <step> run` / `skip (<app> not enabled)`) without docker or a database. Features map to munin
module keys by directory (`entirius_tests.munin.FEATURE_MODULES`, `required_modules(path)`; `features/admin/` by file
prefix): `before_feature` skips a feature whose module the public registry does not list, with the reason `module
'<key>' not installed (munin registry)`, and a scenario tag `@module-<key>` does the same for one scenario. A new
feature directory or admin prefix goes into the map (`tests/test_feature_modules.py` fails on an unmapped file).
