# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The `images/` directory: the catalog's local image files, organised by SKU."""

import shutil
from pathlib import Path

from entirius_tests.data_package.catalog import Catalog
from entirius_tests.data_package.csvs import image_path


def copy_images(catalog: Catalog, out: Path) -> list[str]:
    """Copy every product image to `images/<SKU>/<n><ext>`; returns the paths relative to `out`."""
    copied = []
    for product in catalog.products:
        for number, source in enumerate(product.images, 1):
            target = image_path(product.sku, number, source)
            (out / target).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, out / target)
            copied.append(target)
    return copied
