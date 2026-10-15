# AI studio e2e

Browser tests of the AI studio in the admin CMS: `e2e/cms/test_ai_studio_*.py` (Python Playwright). The stack talks to
an AI toolbox that serves only `fake` models, so every AI answer is a deterministic "Lorem ipsum …" placeholder; the
tests check the flows and count the AI calls in the toolbox tracker, never the wording.

```bash
E2E_CMS_URL=http://localhost:8080 uv run --extra e2e pytest -q e2e/cms/test_ai_studio_*.py
```

| File | Scenario |
|---|---|
| `test_ai_studio_product.py` | 1 product drawer: template run → cards per field × language with costs → "Shorter" → version 2 with its changes → restore v1 → Apply (form field updated, unsaved edits kept); 2 product list bulk run → compact Review rows → detail panel → "Correct all" → version 2 on every proposal |
| `test_ai_studio_seo.py` | 3 SEO research on two products of one category: research once per language, brief in Memory with its expiry |
| `test_ai_studio_profile.py` | 4 profile fact + rule (version +1) → QA warnings on a hand-edited proposal → "Add to facts" → "Fix warnings" → promote the suggestion |
| `test_ai_studio_templates.py` | 5 templates: create, reorder, deactivate; the product drawer follows |
| `test_ai_studio_article.py` | 6 Studio article: brief → questions; not yet run (needs the toolbox SEO app): search phrases → outline (one correction) → draft → metadata → document → ContentDB draft, unpublished, run cost |
| `test_ai_studio_errors.py` | 7 a toolbox 400 → failed task row with the template label, no error code, no worker key; an incomplete profile → Studio soft gate and config health |
| `test_ai_studio_lanes.py` | 8 run lanes: one product "Run now" → done; a list selection "Add to queue" behind an API blocker run → "Queued" in Tasks → done; repeating a run in flight → "2 products skipped", then 409 "already in progress" |

Shared code: `src/entirius_tests/ai_studio_e2e.py` (enrichment admin API, toolbox tracker, screenshot gallery) and
`src/entirius_tests/ai_studio_pages.py` (product AI drawer, product-list AI bulk action).

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `E2E_CMS_URL` | `CMS_BASE_URL` (`http://localhost:8180`) | the CMS under test |
| `API_BASE_URL` | `http://localhost:8100` | the service (setup and reset by API) |
| `TOOLBOX_URL` | `http://localhost:8010` | the AI toolbox the stack uses |
| `TOOLBOX_USERNAME` / `TOOLBOX_PASSWORD` | `admin` / `admin` | toolbox staff login — the tracker usage records are staff-only |
| `AI_TOOLBOX_CHANNEL` | `zeno-test` | the toolbox channel of the stack |
| `E2E_CHANNEL` | `default-europe` | the PIM channel the products are written for |
| `E2E_SCREENSHOT_DIR` | `<zeno>/.playwright-mcp/ai-studio/` | the gallery: `<nn>-<screen>-desktop.png` (1280 × 800) and `-phone.png` (390 × 844) |

## Determinism and re-runs

- Every test resets what it touches by API first: pending proposals of its products are rejected, its templates
  (key prefix `bdd-`) deleted, SEO briefs of products dropped. It re-runs on one seed.
- What a test changes on seeded data is saved back afterwards: the EN meta description it applies (scenario 1),
  template positions (5), the company profile and the channel overlay (4, 7 — as new profile versions).
- The SEO scenario is skipped, and the article scenario stops with a skip after its questions step, while the
  toolbox has no SEO app (`/api/ai-seo/` missing from its OpenAPI schema). The schema is read once per session at
  test time; a toolbox that is down or answers an error fails those tests instead of skipping them.
- Fake models never write "e-commerce" or a number, so scenario 4 brings them in with a manual edit (a manual edit is
  a version and is QA-checked like an AI one), and mark every question optional, so scenario 6 checks the
  required-answer error only when a question is required (otherwise the run reports a warning that it was not
  exercised).
- The toolbox has no error switch for fake models: scenario 7 forces a 400 with a template whose JSON answer schema
  is not a valid JSON Schema, made and spawned by API on a product (the CMS runs workflow-step templates only inside
  a Studio run). The incomplete profile is an empty company profile, saved back after the test.
- Desktop screens: the tests are `desktop_only` (skipped under `E2E_DEVICE`); the phone screenshots come from a
  resized viewport.
