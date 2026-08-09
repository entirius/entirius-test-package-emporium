# Brand book: Emporium — the orbital trading station

The universe behind the Emporium demo dataset. Everything in `package/`, `fixtures/` and `images/`
(brands, series, categories, product names, copy tone) follows this document. Change the universe
here first, then the data.

Data contract: SKUs (`ENT-*`), EANs, prices, channels, CSV structure and feature keys are the
dataset's identity — content (names, descriptions, images) is themed by this brand book.

## The world

The **Emporium** trading station supplies ships, orbital stations and colonies with furniture and
interior fittings. House manufacturer: **Orbital Foundry**. Tone: a professional catalog with a wink
("vacuum-tested", "certified for artificial gravity"). Data languages: EN/PL/ES/DE (EN is the source;
translations stay consistent with it).

All names are 100% original — no terms borrowed from existing fictional universes.

## Brand and badges

| What | idx | Name (EN, all languages) |
|---|---|---|
| brand | `orbital-foundry` | Orbital Foundry |
| badge new | `new` | Just Docked |
| badge bestseller | `bestseller` | Crew Favorite |
| badge sale | `sale` | Cargo Clearance |

## Series (collections) — 10

| idx | Name (EN) |
|---|---|
| orion | Orion Collection |
| nebula | Nebula Heritage |
| heliox | Heliox Works |
| outpost | Outpost Line |
| eclipse | Eclipse Edition |
| quasar | Quasar Series |
| borealis | Borealis Frontier |
| umbra | Umbra Collection |
| magnetar | Magnetar Line |
| solaris | Solaris Collection |

## Options (materials) — 8

| idx | Name (EN) |
|---|---|
| ceramic-composite | Ceramic Composite |
| alloy-mesh | Alloy Mesh |
| synth-leather | Synth Leather |
| titanium-frame | Titanium Frame |
| graphene-finish | Graphene Finish |
| anodized-gold | Anodized Gold |
| meteorite-inlay | Meteorite Inlay |
| nano-chrome | Nano-Chrome |

## Station-themed categories — 8 (rest of the tree is generic furniture)

| idx | Name (EN) |
|---|---|
| lighting | Station Lighting |
| wall-decor | Wall Decor |
| cargo-storage | Cargo Storage |
| galley | Galley Furnishings |
| study | Study & Training |
| bathroom | Bathroom Fittings |
| hydroponics | Hydroponics Decor |
| command-deck | Command Deck Workspace |

## Products — 33 (EN names; PL/ES/DE translated consistently, url-keys slugified from names)

| SKU | Name (EN) | | SKU | Name (EN) |
|---|---|---|---|---|
| ENT-S001 | Orion Command Sofa | | ENT-B002 | Starlight Nightstand |
| ENT-S002 | Nebula Crimson Sofa | | ENT-B003 | Airlock Dresser |
| ENT-S003 | Umbra Sectional | | ENT-B004 | Freighter Wardrobe |
| ENT-S004 | Borealis Frontier Sofa | | ENT-B005 | Corvette Vanity |
| ENT-S005 | Outpost Bastion Sofa | | ENT-D001 | Command Deck Desk |
| ENT-S006 | Magnetar Sleeper Sofa | | ENT-D002 | Quartermaster Writing Desk |
| ENT-C001 | Flight Deck Command Chair | | ENT-D003 | Star-Chart Bookshelf |
| ENT-C002 | Docking Bay Chair | | ENT-D004 | Engineer Filing Cabinet |
| ENT-C003 | Zero-G Recliner | | ENT-X001 | Solar Deck Lounger |
| ENT-C004 | Observation Deck Lounge Chair | | ENT-X002 | Promenade Bench |
| ENT-C005 | Stationmaster Office Chair | | ENT-X003 | Habitat Dome Chair |
| ENT-C006 | Navigator Swivel Chair | | ENT-CFG01 | Captain's Living Room Set |
| ENT-O001 | Cargo Pod Ottoman | | ENT-CFG02 | Stationmaster's Office Set |
| ENT-O002 | Drone Dock Ottoman | | ENT-BND01 | Commander's Comfort Bundle |
| ENT-O003 | Escape Pod Ottoman | | ENT-BND02 | Deep Sleep Bundle |
| ENT-O004 | Satellite Ottoman | | ENT-CUS01 | Chief Engineer's Custom Throne |
| ENT-B001 | Cryo-Bay Platform Bed | | 1C01/N, 2R04/NR | Slash Chair N / NR (technical SKUs) |

## Copy, texts, feeds

- Product copy (`short_description en`, `description en`, `material_composition`): station-catalog
  tone, materials named after the options above (e.g. "Ceramic-composite frame with synth-leather
  upholstery").
- `specifications` JSON, `material_grade`: tier vocabulary — Flagship / Station / Colony / Frontier /
  Deep-Space / Orbital; generic English words (Tactical, Scout, Naval, Command…) are fine.
- Supplier feeds: producer `Orbital Foundry Supply`; product names follow the map above.
- Supplier brands used in tests: `novatrade`, `Kestrel Supply`.
- CMS content (contentdb): blog posts and pages written in the station's voice.

## Images

- Target: renders generated with image models. Prompt style: "product photo, single furniture piece,
  clean studio background, spaceship-interior design language, brushed metal + warm textiles,
  soft lighting".
- Interim (until generation): programmatic placeholders (Pillow) — a tile with SKU, name and the
  series color; directory structure `images/<SKU>/N.png`.

## Definition of Done for dataset changes

- No terms from existing fictional universes anywhere in the repo.
- CSV structure untouched (column/row counts), SKU/EAN/prices identical.
- `behave --dry-run` scenario count unchanged; package import passes against a running service.
