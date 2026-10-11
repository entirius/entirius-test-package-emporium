# Data package from your own catalog

`python -m entirius_tests.data_package` turns two files of your own into a data package in the layout the platform
imports. It reads local files only and never opens a network connection.

- **`profile.yaml`**: one channel with its `idx`, name, currency, languages, default country and tax rate
  ([example](https://github.com/entirius/entirius-test-package-emporium/blob/develop/examples/data-package/profile.yaml)).
  It is not the seed profile of the seed script (`SEED_PROFILE`).
- **A catalog file**, JSON or CSV: categories and products, each product with a name, a price and a category; slug,
  description, SKU, quantity, brand and local image files are optional
  ([JSON](https://github.com/entirius/entirius-test-package-emporium/blob/develop/examples/data-package/catalog.json),
  [CSV](https://github.com/entirius/entirius-test-package-emporium/blob/develop/examples/data-package/catalog.csv)).

```bash
uv run --extra data python -m entirius_tests.data_package build --profile <profile.yaml> --catalog <catalog.json|csv> --out <dir> [--mount <path>]
uv run --extra data python -m entirius_tests.data_package validate <dir>
make data-package PROFILE=<profile.yaml> CATALOG=<catalog.json|csv> OUT=<dir>    # build, then validate
```

`--out` must be new or empty; the same input always gives the same bytes. `--mount` is the path the package has where
the service and the worker read it (default: the absolute path of `--out`); the quantity storage points at it.
`validate` reads a built package back: every listed file exists, the channel is the same everywhere, and every
product has its category, a price row, a quantity row and its image files.

```
<dir>/
├── package/
│   ├── volkanos-config/        # channels.conf, pim-channels.csv, pim-features*.csv
│   ├── attributes--brand.csv
│   ├── categories--<idx>.csv   # a root row first, then the catalog tree
│   ├── products--<idx>.csv     # name, URL key and description in every profile language
│   ├── pricelist--<idx>.csv
│   └── qty.csv
├── images/<SKU>/<n>.<ext>      # the catalog's image files, by SKU
├── fixtures/                   # the channel in regional, pim, pricemanager, qms, checkout, matrix, accounts
├── first-channel.toml          # config of the service's first-channel script
└── manifest.json               # channel, mount, fixtures in load order, counts, files
```

The fixtures fit an empty, migrated database and give the channel pk 1 in every module, with one shipping method, one
payment method and one tax rate as a starting point. Not generated: content pages, FAQ, mail templates, delivery
points, discounts, agreements, API keys, users. The storefront is configured as
[its own repository](https://github.com/entirius/entirius-pwa-storefront) describes. File formats and the import
order: [Data Import](https://docs.entirius.com/build/data-import/).
