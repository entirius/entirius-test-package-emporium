# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Generate the `fixtures/lookup/` calibration set (dev-plan 09, test-strategy.md §4).

Deterministic (fixed RNG seed): re-running this script reproduces byte-identical output, so the
generated files are committed like any other fixture — nothing here runs at seed time.

Design — six adversarial pair classes (test-strategy.md §4), ten pairs each, one PIM `RealProduct`
and one atlas `SourceProduct` per pair:

  exact_dup         same GTIN, same brand/name, different (independently shot) photo -> match
  variant           same brand, colour word differs, different GTIN                  -> variant
  multipack         single unit vs N-pack of the same name, different GTIN, weight x3 -> no
  dirty_ean         same GTIN, name identical, brand corrupted on one side           -> match
  name_only         no EAN either side, name+brand near-identical, weight in tol.     -> match
  photo_lookalike   unrelated products (different brand/name/EAN) sharing a photo    -> no
                    template, to probe image-only false positives

Every brand/product name is invented — no real trademarks, no scraped images (Pillow shapes only).

Output:
  fixtures/lookup/pim_products.json     ~60 RealProduct definitions
  fixtures/lookup/atlas_products.json   ~60 SourceProduct definitions (2 sources)
  fixtures/lookup/img/*.png             synthetic product shots (Pillow: shape + text on white)
  fixtures/lookup/labelled_pairs.csv    >= 200 labelled pairs for `lookup_eval`

Run: `uv run --extra dev python scripts/generate-lookup-fixtures.py` (repo root).
"""

import itertools
import json
import random
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw

SEED = 20260823
RNG = random.Random(SEED)  # noqa: S311 — reproducible fixture generation, not cryptography

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures" / "lookup"
IMG_DIR = FIXTURES_DIR / "img"
FIXTURES_HOST = "http://fixtures:8000"  # in-network only (docker-compose.yml `fixtures` service)

SOURCE_A = "atl-lookup-a"
SOURCE_B = "atl-lookup-b"

BRANDS = [
    "Kestrel",
    "Boreal",
    "Anvora",
    "Petrichor",
    "Cindra",
    "Halvorn",
    "Ombrix",
    "Talveri",
    "Sundrift",
    "Northcraft",
]
CATEGORIES = [
    "Kettle",
    "Backpack",
    "Office Chair",
    "Desk Lamp",
    "Blender",
    "Headphones",
    "Toaster",
    "Yoga Mat",
    "Water Bottle",
    "Bluetooth Speaker",
]
COLORS = ["black", "white", "red", "blue", "green", "grey"]
SHAPES = ["ellipse", "rectangle", "triangle"]
PALETTE = [(214, 61, 61), (61, 122, 214), (67, 163, 89), (219, 168, 52), (142, 84, 199), (74, 74, 74)]

PAIRS_PER_CLASS = 10
IMG_SIZE = 220


@dataclass(frozen=True)
class PimProduct:
    sku: str
    ean: str
    brand: str
    name: str
    weight_kg: float
    image: str
    pair_class: str
    pair_index: int
    mpn: str = ""


@dataclass(frozen=True)
class AtlasProduct:
    source_idx: str
    external_id: str
    ean: str
    brand: str
    name: str
    weight_kg: float
    image: str
    pair_class: str
    pair_index: int
    mpn: str = ""


@dataclass(frozen=True)
class LabelledPair:
    query_kind: str
    query_ref: str
    candidate_kind: str
    candidate_ref: str
    label: str
    why: str


def _check_digit(base12: str) -> str:
    """EAN-13 check digit: odd positions (1-indexed) weight 1, even positions weight 3."""
    total = sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(base12))
    return str((10 - total % 10) % 10)


class _EanSequence:
    def __init__(self, start: int = 1_000_000) -> None:
        self._next = start

    def new(self) -> str:
        base12 = f"590{self._next:09d}"
        self._next += 1
        return base12 + _check_digit(base12)


EANS = _EanSequence()


def atlas_ref(source_idx: str, external_id: str) -> str:
    return f"{source_idx}:{external_id}"


def _draw_image(filename: str, template_key: str, text: str) -> None:
    """`template_key` picks the shape/colour combo — a plain per-pair index would let two classes
    that land on the same index *and* end up with the same text (e.g. `exact_dup`/`dirty_ean`/
    `multipack` all reuse `f"{brand} {category}"` for `i=0`) render byte-identical PNGs, tripping
    `Picture.sha1`'s unique constraint once seeded. Hashing the filename keeps every template
    distinct except where a class explicitly wants to share one (`photo_lookalike`) — and a tiny
    filename watermark (top-left corner) guarantees every PNG is byte-unique even when two classes
    coincidentally land on the same shape/colour/text combination (dirty_ean: text is identical by
    design, only the corner watermark tells the files apart)."""
    template_id = zlib.crc32(template_key.encode())
    shape = SHAPES[template_id % len(SHAPES)]
    color = PALETTE[template_id % len(PALETTE)]
    image = Image.new("RGB", (IMG_SIZE, IMG_SIZE), "white")
    draw = ImageDraw.Draw(image)
    pad = 30
    box = (pad, pad, IMG_SIZE - pad, IMG_SIZE - pad)
    if shape == "ellipse":
        draw.ellipse(box, fill=color)
    elif shape == "rectangle":
        draw.rectangle(box, fill=color)
    else:
        draw.polygon([(IMG_SIZE / 2, pad), (pad, IMG_SIZE - pad), (IMG_SIZE - pad, IMG_SIZE - pad)], fill=color)
    draw.text((8, IMG_SIZE - 20), text[:28], fill=(20, 20, 20))
    draw.text((4, 4), filename[:24], fill=(160, 160, 160))  # tiny watermark: guarantees a unique sha1 per file
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    image.save(IMG_DIR / filename, format="PNG", optimize=True)


def _weight(base_grams: int, index: int) -> float:
    return round((base_grams + index * 37) / 1000, 3)


# Every (class, i) gets its own brand/category identity — a plain `i % len(BRANDS)` would let two
# classes at the same `i` land on the identical "Kestrel Kettle" (both classes share the 0..9 index
# range), flooding the blocking pool with cross-class false positives once seeded. Slicing a
# shuffled list of all brand x category combinations keeps every one of the 60 pairs unique.
_BRAND_CATEGORY_COMBOS = list(itertools.product(range(len(BRANDS)), range(len(CATEGORIES))))
RNG.shuffle(_BRAND_CATEGORY_COMBOS)


def _brand_category(class_index: int, i: int) -> tuple[str, str]:
    brand_idx, category_idx = _BRAND_CATEGORY_COMBOS[class_index * PAIRS_PER_CLASS + i]
    return BRANDS[brand_idx], CATEGORIES[category_idx]


def _other_brand(brand: str) -> str:
    return BRANDS[(BRANDS.index(brand) + 3) % len(BRANDS)]


def _other_category(category: str) -> str:
    return CATEGORIES[(CATEGORIES.index(category) + 4) % len(CATEGORIES)]


def _color(i: int) -> str:
    return COLORS[i % len(COLORS)]


def _other_color(i: int) -> str:
    return COLORS[(i + 1) % len(COLORS)]


def _source_for(i: int) -> str:
    return SOURCE_A if i % 2 == 0 else SOURCE_B


def _make_exact_dup(class_index: int, i: int) -> tuple[PimProduct, AtlasProduct, str, str]:
    ean = EANS.new()
    brand, category = _brand_category(class_index, i)
    name = f"{brand} {category}"
    weight = _weight(500, i)
    atlas_name = f"{name} ({brand})"
    pim_img, atl_img = f"exact_dup-{i:02d}-pim.png", f"exact_dup-{i:02d}-atlas.png"
    _draw_image(pim_img, pim_img, name)
    _draw_image(atl_img, atl_img, atlas_name)  # independently shot: different template AND text
    pim = PimProduct(f"LKP-PIM-EXACT-{i:02d}", ean, brand, name, weight, pim_img, "exact_dup", i)
    atlas = AtlasProduct(_source_for(i), f"EXACT-{i:02d}", ean, brand, atlas_name, weight, atl_img, "exact_dup", i)
    why = "Same GTIN, brand and name — canonical duplicate seen through two feeds, each with its own product shot."
    return pim, atlas, "match", why


def _make_variant(class_index: int, i: int) -> tuple[PimProduct, AtlasProduct, str, str]:
    """Same brand + MPN (the model number) on both sides — an `identifier_exact` signal — so the
    colour conflict caps the verdict at `review` (research r02 §4) instead of falling all the way
    to `no_match` for lack of any other identifier. Mirrors `test_colour_variant_is_review_not_match`
    in the lookup module's own test suite."""
    brand, category = _brand_category(class_index, i)
    color, other_color = _color(i), _other_color(i)
    weight = _weight(600, i)
    mpn = f"MOD-{i:02d}"
    pim_img, atl_img = f"variant-{i:02d}-pim.png", f"variant-{i:02d}-atlas.png"
    _draw_image(pim_img, pim_img, f"{category} {color}")
    _draw_image(atl_img, atl_img, f"{category} {other_color}")
    pim = PimProduct(
        f"LKP-PIM-VARIANT-{i:02d}",
        EANS.new(),
        brand,
        f"{brand} {category} {color}",
        weight,
        pim_img,
        "variant",
        i,
        mpn,
    )
    atlas = AtlasProduct(
        _source_for(i),
        f"VARIANT-{i:02d}",
        EANS.new(),
        brand,
        f"{brand} {category} {other_color}",
        weight,
        atl_img,
        "variant",
        i,
        mpn,
    )
    why = "Same brand + MPN, colour differs, each side has its own EAN — sibling variant: review, never match."
    return pim, atlas, "variant", why


def _make_multipack(class_index: int, i: int) -> tuple[PimProduct, AtlasProduct, str, str]:
    brand, category = _brand_category(class_index, i)
    name = f"{brand} {category}"
    weight = _weight(400, i)
    pim_img, atl_img = f"multipack-{i:02d}-pim.png", f"multipack-{i:02d}-atlas.png"
    _draw_image(pim_img, pim_img, name)
    _draw_image(atl_img, atl_img, f"{name} 3-pack")
    pim = PimProduct(f"LKP-PIM-MULTI-{i:02d}", EANS.new(), brand, name, weight, pim_img, "multipack", i)
    atlas = AtlasProduct(
        _source_for(i),
        f"MULTI-{i:02d}",
        EANS.new(),
        brand,
        f"{name} 3-pack",
        round(weight * 3, 3),
        atl_img,
        "multipack",
        i,
    )
    why = "Single unit vs a 3-pack of the same item — text looks near-identical, weight and GTIN do not agree."
    return pim, atlas, "no", why


def _make_dirty_ean(class_index: int, i: int) -> tuple[PimProduct, AtlasProduct, str, str]:
    ean = EANS.new()
    brand, category = _brand_category(class_index, i)
    name = f"{brand} {category}"
    weight = _weight(700, i)
    pim_img, atl_img = f"dirty_ean-{i:02d}-pim.png", f"dirty_ean-{i:02d}-atlas.png"
    _draw_image(pim_img, pim_img, name)
    _draw_image(atl_img, atl_img, name)
    pim = PimProduct(f"LKP-PIM-DIRTY-{i:02d}", ean, brand, name, weight, pim_img, "dirty_ean", i)
    atlas = AtlasProduct(
        _source_for(i), f"DIRTY-{i:02d}", ean, _other_brand(brand), name, weight, atl_img, "dirty_ean", i
    )
    why = (
        "Same GTIN and product name; the atlas feed's brand field is corrupted (dirty data) — still one "
        "product (human ground truth). The engine currently CAPS this at review, not match — brand_conflict "
        "is a capping flag even when gtin_exact identifies the pair (scoring.py CAPPING_FLAGS); label is the "
        "human verdict on purpose, pending an operator decision on whether the engine should agree."
    )
    return pim, atlas, "match", why


def _make_name_only(class_index: int, i: int) -> tuple[PimProduct, AtlasProduct, str, str]:
    brand, category = _brand_category(class_index, i)
    weight = _weight(300, i)
    pim_img, atl_img = f"name_only-{i:02d}-pim.png", f"name_only-{i:02d}-atlas.png"
    _draw_image(pim_img, pim_img, f"{category} Edition")
    _draw_image(atl_img, atl_img, f"{category} edition")
    pim = PimProduct(
        f"LKP-PIM-NAMEONLY-{i:02d}", "", brand, f"{brand} {category} Edition", weight, pim_img, "name_only", i
    )
    atlas = AtlasProduct(
        _source_for(i),
        f"NAMEONLY-{i:02d}",
        "",
        brand,
        f"{brand} {category} edition",
        round(weight * 1.03, 3),
        atl_img,
        "name_only",
        i,
    )
    why = (
        "No EAN on either side; name and brand near-identical, weight within tolerance — fuzzy-name only "
        "match (human ground truth). The engine currently lands this at review (score ~60 < the 75 match "
        "threshold, no identifier to force it higher) — label is the human verdict on purpose, pending an "
        "operator decision on whether the threshold or the label should move."
    )
    return pim, atlas, "match", why


def _make_photo_lookalike(class_index: int, i: int) -> tuple[PimProduct, AtlasProduct, str, str]:
    brand, category = _brand_category(class_index, i)
    other_brand, other_category = _other_brand(brand), _other_category(category)
    weight_a, weight_b = _weight(450, i), _weight(900, i)
    shared_template = f"photo_lookalike-{i:02d}-shared"  # both sides render from the SAME template
    pim_img, atl_img = f"photo_lookalike-{i:02d}-pim.png", f"photo_lookalike-{i:02d}-atlas.png"
    _draw_image(pim_img, shared_template, f"{brand} {category}")
    _draw_image(atl_img, shared_template, f"{other_brand} {other_category}")
    pim = PimProduct(
        f"LKP-PIM-PHOTO-{i:02d}", EANS.new(), brand, f"{brand} {category}", weight_a, pim_img, "photo_lookalike", i
    )
    atlas = AtlasProduct(
        _source_for(i),
        f"PHOTO-{i:02d}",
        EANS.new(),
        other_brand,
        f"{other_brand} {other_category}",
        weight_b,
        atl_img,
        "photo_lookalike",
        i,
    )
    why = "Unrelated products (different brand/name/GTIN) rendered from the same photo template — image alone must not promote this to a match."
    return pim, atlas, "no", why


_CLASS_BUILDERS = {
    "exact_dup": _make_exact_dup,
    "variant": _make_variant,
    "multipack": _make_multipack,
    "dirty_ean": _make_dirty_ean,
    "name_only": _make_name_only,
    "photo_lookalike": _make_photo_lookalike,
}


def _build_pairs() -> list[tuple[PimProduct, AtlasProduct, str, str]]:
    pairs = []
    for class_index, builder in enumerate(_CLASS_BUILDERS.values()):
        for i in range(PAIRS_PER_CLASS):
            pairs.append(builder(class_index, i))
    return pairs


def _random_negatives(pairs: list[tuple[PimProduct, AtlasProduct, str, str]], per_pim: int = 2) -> list[LabelledPair]:
    """Every PIM product paired with `per_pim` atlas candidates from a DIFFERENT pair class."""
    rows = []
    atlas_by_class: dict[str, list[AtlasProduct]] = {}
    for _pim, atlas, _label, _why in pairs:
        atlas_by_class.setdefault(atlas.pair_class, []).append(atlas)
    for pim, _atlas, _label, _why in pairs:
        other_classes = [c for c in atlas_by_class if c != pim.pair_class]
        for cls in RNG.sample(other_classes, per_pim):
            atlas = RNG.choice(atlas_by_class[cls])
            rows.append(
                LabelledPair(
                    query_kind="pim_product",
                    query_ref=pim.sku,
                    candidate_kind="atlas_source_product",
                    candidate_ref=atlas_ref(atlas.source_idx, atlas.external_id),
                    label="no",
                    why="Random negative: unrelated products sampled across families — negative baseline.",
                )
            )
    return rows


def _labelled_pairs(pairs: list[tuple[PimProduct, AtlasProduct, str, str]]) -> list[LabelledPair]:
    rows = []
    for pim, atlas, label, why in pairs:
        cand = atlas_ref(atlas.source_idx, atlas.external_id)
        rows.append(LabelledPair("pim_product", pim.sku, "atlas_source_product", cand, label, why))
        rows.append(LabelledPair("atlas_source_product", cand, "pim_product", pim.sku, label, f"reverse: {why}"))
    rows.extend(_random_negatives(pairs))
    return rows


def _write_json(path: Path, rows: list) -> None:
    path.write_text(json.dumps([asdict(row) for row in rows], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[LabelledPair]) -> None:
    import csv

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["query_kind", "query_ref", "candidate_kind", "candidate_ref", "label", "why"])
        for row in rows:
            writer.writerow([row.query_kind, row.query_ref, row.candidate_kind, row.candidate_ref, row.label, row.why])


def main() -> None:
    pairs = _build_pairs()
    pim_products = [pim for pim, _atlas, _label, _why in pairs]
    atlas_products = [atlas for _pim, atlas, _label, _why in pairs]
    labelled = _labelled_pairs(pairs)

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(FIXTURES_DIR / "pim_products.json", pim_products)
    _write_json(FIXTURES_DIR / "atlas_products.json", atlas_products)
    _write_csv(FIXTURES_DIR / "labelled_pairs.csv", labelled)

    print(f"pim_products.json: {len(pim_products)} rows")
    print(f"atlas_products.json: {len(atlas_products)} rows")
    print(f"labelled_pairs.csv: {len(labelled)} rows")
    print(f"images: {len(list(IMG_DIR.glob('*.png')))} files in {IMG_DIR}")


if __name__ == "__main__":
    main()
