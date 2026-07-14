# Emporium demo dataset

Default Volkanos test package. Seeds a fresh database with channels, products, prices,
and quantities so the API is immediately functional.

> Theme: **Emporium** — a space-trading station outfitting ships, orbital stations, and
> colonies with furniture and interior fittings; in-house producer **Orbital Foundry**
> (original names, LLM-generated imagery). Structure, SKUs (`ENT-*`), EANs, prices, and
> channels stay stable across the re-theme.

## Channels

| Channel | Languages | Currencies | Country |
|---------|-----------|------------|---------|
| `default-local` | EN | USD | US |
| `default-europe` | EN (default), ES, DE, PL | EUR (default), PLN | DE, PL, ES, FR |

## Product catalog (33 products per channel)

| SKU range | Category | Type |
|-----------|----------|------|
| ENT-S001–S006 | sofas | simple |
| ENT-C001–C006 | chairs | simple |
| ENT-O001–O004 | ottomans | simple |
| ENT-B001–B005 | bedroom | simple |
| ENT-D001–D004 | office | simple |
| ENT-X001–X003 | outdoor | simple |
| ENT-CFG01–02 | sets | configurable (children among the simples) |
| ENT-BND01–02 | bundles | bundle (min/max limits) |
| ENT-CUS01 | custom | custom product |

Attributes: 10 series, 8 options, 3 badges, 1 brand — see `attributes--*.csv`.
PIM features: 13 system + 12 global (incl. DECIMAL, BOOL, TEXT, JSON types); 5 feature sets.
Matrix config: filterable (series, options, badge, brand, is_handcrafted), searchable
(material_composition), sortable (weight_kg) — per channel.

Categories nest up to level 5 (15 L1 categories) for breadcrumb, tree-traversal and
menu-scrolling tests — see `categories--*.csv`.

<!-- TODO: CUSTOM PRODUCTS - ENT-CUS01 is imported but not fully tested.
     The Matrix custom_details/ endpoint returns 500 (upstream bug in django-matrix).
     Custom product modifiers, custom pricing, and the custom_details API need
     test coverage once the upstream issue is resolved. -->

<!-- NOTE: PRODUCT ATTRIBUTE IMAGES - product-attribute-images-import-from-csv
     writes to ProductAttributeImage (variant swatches), not exposed through any
     public API (Matrix). No BDD coverage possible until an endpoint exists. -->

## Import pipeline (10 steps)

1. **Fixtures** — `loaddata --format=yaml` (includes discount rules)
2. **PIM config** — channels, features, feature-sets, feature positions
3. **Attributes** — badge, brand, series, options
4. **Categories** — per channel
5. **Products** — 33 products per channel (with pictures if `../images/` exists)
6. **Positions** — product ordering per channel
7. **Prices** — USD + EUR + `manage-pricelists` + bundle component prices
8. **Thumbnails** — `pim-thumbs-generate` per channel (WebP 90%, 5 square sizes: 160–1400px)
9. **QMS** — quantities (requires Celery)
10. **Matrix** — read model generation

Entry points: `../scripts/seed.sh` (host side) →
`../scripts/import-package.sh` (container side).

## Devtools — bulk data generation

Post-seed multiplier for stress testing — clones existing seed data to generate large
volumes (products, categories, feature sets, attributes, pictures, links).
See [`../devtools/README.md`](../devtools/README.md).

## Discount rules (10 test rules)

Simple (percent, fixed), gratis products (cheapest, most expensive, progressive),
free shipping, progressive steps, automatic application, combinable rules, user targeting.
See [`../DISCOUNT_RULES.md`](../DISCOUNT_RULES.md).
