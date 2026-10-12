# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The data package tool: build from the example files, validate, and refuse bad input."""

import csv
import json
import shutil
import tomllib
from pathlib import Path

import pytest
import yaml

from entirius_tests.data_package.catalog import load_catalog
from entirius_tests.data_package.cli import main
from entirius_tests.data_package.profile import load_profile

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "data-package"
IDX = "demo-shop"
FIRST_CHANNEL_KEYS = {"idx", "name", "default_language", "languages", "default_currency", "currencies", "country"}


def _build(out: Path, catalog: str = "catalog.json", *extra: str) -> int:
    inputs = ["--profile", str(EXAMPLE / "profile.yaml"), "--catalog", str(EXAMPLE / catalog)]
    return main(["build", *inputs, "--out", str(out), *extra])


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _tree(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


@pytest.fixture
def package(tmp_path: Path) -> Path:
    assert _build(tmp_path / "out") == 0
    return tmp_path / "out"


@pytest.fixture
def profile_data() -> dict:
    return yaml.safe_load((EXAMPLE / "profile.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def catalog_dir(tmp_path: Path) -> Path:
    """A copy of the example a test can break: catalog.json plus its images."""
    return Path(shutil.copytree(EXAMPLE, tmp_path / "example"))


def _load_broken_profile(tmp_path: Path, data: dict) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    load_profile(path)


def _load_broken_catalog(catalog_dir: Path, change) -> None:
    data = json.loads((catalog_dir / "catalog.json").read_text(encoding="utf-8"))
    change(data["products"])
    (catalog_dir / "catalog.json").write_text(json.dumps(data), encoding="utf-8")
    load_catalog(catalog_dir / "catalog.json", load_profile(EXAMPLE / "profile.yaml"))


def test_example_builds_and_validates(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    package = tmp_path / "out"
    assert _build(package) == 0
    assert main(["validate", str(package)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert f"data-package: done {IDX} -> {package}" in lines
    assert "data-package: wrote package/qty.csv" in lines
    assert lines[-1] == f"data-package: valid {IDX} (4 categories, 6 products, 4 images)"


def test_json_and_csv_examples_give_the_same_package(package: Path, tmp_path: Path) -> None:
    assert _build(tmp_path / "from-csv", "catalog.csv", "--mount", str(package)) == 0
    assert _tree(tmp_path / "from-csv") == _tree(package)


def test_second_build_is_byte_identical(package: Path, tmp_path: Path) -> None:
    assert _build(tmp_path / "again", "catalog.json", "--mount", str(package)) == 0
    assert _tree(tmp_path / "again") == _tree(package)


def test_non_empty_out_is_refused(package: Path, capsys: pytest.CaptureFixture) -> None:
    assert _build(package) == 1
    assert f"data-package: error: {package}: the output directory exists and is not empty" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("key", "value", "named"),
    [
        ("idx", None, "channel.idx"),
        ("currency", "XXX", "channel.currency"),
        ("default_language", "pl", "channel.default_language"),
        ("default_country", "ZZ", "channel.default_country"),
        ("tax_rate", "19", "channel.tax_rate"),
        ("tax_rate", "NaN", "channel.tax_rate"),
        ("languages", ["en", "en"], "channel.languages"),
    ],
)
def test_bad_profile_names_the_key(tmp_path: Path, profile_data: dict, key: str, value, named: str) -> None:
    profile_data["channel"][key] = value
    with pytest.raises(ValueError, match=named):
        _load_broken_profile(tmp_path, profile_data)


def test_unknown_currency_lists_the_known_codes(tmp_path: Path, profile_data: dict) -> None:
    profile_data["channel"]["currency"] = "XXX"
    with pytest.raises(ValueError, match="known: .*EUR.*USD"):
        _load_broken_profile(tmp_path, profile_data)


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda products: products[0].update(category_slug="nowhere"), "unknown category_slug: nowhere"),
        (lambda products: products[1].update(sku="DEMO-TEA-1"), "duplicate sku: DEMO-TEA-1"),
        (lambda products: products[1].update(slug="black-tea-100g"), "duplicate product slug: black-tea-100g"),
        (lambda products: products[0].update(images=["https://example.com/a.png"]), "product 1: images are local"),
        (lambda products: products[0].update(images=["images/none.png"]), "product 1: image file .* does not exist"),
        (lambda products: products[2].update(price="0"), "product 3: price"),
        (lambda products: products[2].pop("name"), "product 3: missing name"),
        (lambda products: products[2].update(price="NaN"), "product 3: price"),
        (lambda products: products[0].update(sku="../../escape"), "product 1: sku"),
        (lambda products: products[0].update(images="images/coffee.png"), "product 1: images must be a list"),
        (lambda products: products[0].update(brand=None), "product 1: brand must be text"),
        (lambda products: products[2].update(name="茶"), "product 3: slug"),
        (lambda products: products.clear(), "at least one"),
        (lambda products: products.append("x"), "list of at least one object"),
    ],
)
def test_bad_catalog_names_the_row(catalog_dir: Path, change, named: str) -> None:
    with pytest.raises(ValueError, match=named):
        _load_broken_catalog(catalog_dir, change)


def test_bad_input_exits_1_and_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = main(
        ["build", "--profile", str(tmp_path / "none.yaml"), "--catalog", "c.json", "--out", str(tmp_path / "o")]
    )
    assert code == 1
    assert capsys.readouterr().out.startswith("data-package: error: ")
    assert not (tmp_path / "o").exists()


def test_skus_prices_and_quantities(package: Path) -> None:
    skus = [row["sku"] for row in _rows(package / "package" / f"products--{IDX}.csv")]
    assert skus == ["DEMO-TEA-1", "DEMO-TEA-2", "DEMO-P001", "DEMO-COF-1", "DEMO-P002", "DEMO-P003"]
    prices = _rows(package / "package" / f"pricelist--{IDX}.csv")
    quantities = {row["sku"]: row["quantity"] for row in _rows(package / "package" / "qty.csv")}
    assert [row["sku"] for row in prices] == skus
    assert {row["tax_class"] for row in prices} == {"standard-rate"}
    assert list(quantities) == skus
    assert (quantities["DEMO-TEA-1"], quantities["DEMO-P001"]) == ("40", "20")


def test_categories_start_with_root_and_keep_the_tree(package: Path) -> None:
    rows = _rows(package / "package" / f"categories--{IDX}.csv")
    assert [(row["idx"], row["parent"], row["position"]) for row in rows] == [
        ("root", "", "0"),
        ("tea", "root", "10"),
        ("green-tea", "tea", "20"),
        ("coffee", "root", "30"),
    ]
    assert rows[2]["name en"] == rows[2]["name de"] == "Green Tea"


def test_images_land_by_sku(package: Path) -> None:
    products = {row["sku"]: row for row in _rows(package / "package" / f"products--{IDX}.csv")}
    assert products["DEMO-TEA-1"]["img main"] == "../images/DEMO-TEA-1/1.png"
    assert products["DEMO-TEA-2"]["images"] == "../images/DEMO-TEA-2/2.png"
    assert products["DEMO-P001"]["img main"] == ""
    assert (package / "images" / "DEMO-TEA-1" / "1.png").read_bytes() == (
        EXAMPLE / "images" / "black-tea.png"
    ).read_bytes()
    assert json.loads((package / "manifest.json").read_text())["counts"]["images"] == 4


def test_fixtures_parse_and_carry_the_channel(package: Path) -> None:
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["fixtures"][:2] == ["django_regional.cfg.yaml", "django_pim.cfg.yaml"]
    for name in manifest["fixtures"][1:]:
        records = yaml.safe_load((package / "fixtures" / name).read_text(encoding="utf-8"))
        channels = [record for record in records if record["model"].endswith(".channel")]
        assert [(record["pk"], record["fields"]["idx"]) for record in channels] == [(1, IDX)], name
    regional = yaml.safe_load((package / "fixtures" / "django_regional.cfg.yaml").read_text(encoding="utf-8"))
    assert [(record["model"], record["fields"]["iso2"]) for record in regional] == [
        ("django_regional.language", "en"),
        ("django_regional.language", "de"),
    ]


def test_channel_files_use_the_currency_forms(package: Path) -> None:
    config = package / "package" / "volkanos-config"
    assert (config / "channels.conf").read_text(encoding="utf-8") == f"{IDX}:EUR\n"
    assert _rows(config / "pim-channels.csv") == [
        {"idx": IDX, "name": "Demo Shop", "default_language": "en", "languages": "en,de"}
        | {"default_currency": "eur", "currencies": "eur"}
    ]


def test_qms_fixture_holds_the_mount(tmp_path: Path) -> None:
    assert _build(tmp_path / "out", "catalog.json", "--mount", "/srv/shop/") == 0
    records = yaml.safe_load((tmp_path / "out" / "fixtures" / "django_qms.cfg.yaml").read_text(encoding="utf-8"))
    paths = [
        record["fields"]["additional_data"].get("csv_path")
        for record in records
        if "additional_data" in record["fields"]
    ]
    assert paths == ["/srv/shop/package/qty.csv", None]


def test_first_channel_toml_has_the_seven_keys(package: Path) -> None:
    with (package / "first-channel.toml").open("rb") as handle:
        channel = tomllib.load(handle)["channel"]
    assert set(channel) == FIRST_CHANNEL_KEYS
    assert (channel["idx"], channel["languages"], channel["currencies"], channel["country"]) == (
        IDX,
        ["en", "de"],
        ["EUR"],
        "DE",
    )


def test_validate_reports_a_removed_pricelist_row(package: Path, capsys: pytest.CaptureFixture) -> None:
    pricelist = package / "package" / f"pricelist--{IDX}.csv"
    lines = pricelist.read_text(encoding="utf-8").splitlines(keepends=True)
    pricelist.write_text("".join(line for line in lines if not line.startswith("DEMO-TEA-2,")), encoding="utf-8")
    assert main(["validate", str(package)]) == 1
    assert "data-package: invalid: product DEMO-TEA-2: no pricelist row" in capsys.readouterr().out


def test_validate_reports_a_missing_file_and_a_foreign_channel(package: Path, capsys: pytest.CaptureFixture) -> None:
    (package / "package" / "volkanos-config" / "channels.conf").write_text("other-shop:EUR\n", encoding="utf-8")
    assert main(["validate", str(package)]) == 1
    assert "channels.conf: channel ['other-shop'] is not ['demo-shop']" in capsys.readouterr().out
    (package / "images" / "DEMO-TEA-1" / "1.png").unlink()
    assert main(["validate", str(package)]) == 1
    assert "invalid: images/DEMO-TEA-1/1.png: listed in manifest.json" in capsys.readouterr().out


def test_csv_with_a_byte_order_mark_keeps_its_skus(catalog_dir: Path) -> None:
    text = (catalog_dir / "catalog.csv").read_text(encoding="utf-8")
    (catalog_dir / "catalog.csv").write_text(text, encoding="utf-8-sig")
    catalog = load_catalog(catalog_dir / "catalog.csv", load_profile(EXAMPLE / "profile.yaml"))
    assert catalog.products[0].sku == "DEMO-TEA-1"


def test_category_cycle_is_refused(catalog_dir: Path) -> None:
    rows = ["name,price,category,parent_category", "A,1,one,two", "B,1,two,one"]
    (catalog_dir / "loop.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="its own ancestor: one, two"):
        load_catalog(catalog_dir / "loop.csv", load_profile(EXAMPLE / "profile.yaml"))


@pytest.mark.parametrize("damage", ["[]", "{}", '{"files": [], "channel": "../x", "fixtures": [], "counts": {}}'])
def test_validate_reports_a_damaged_manifest(package: Path, damage: str, capsys: pytest.CaptureFixture) -> None:
    (package / "manifest.json").write_text(damage, encoding="utf-8")
    assert main(["validate", str(package)]) == 1
    assert "data-package: invalid: " in capsys.readouterr().out
