# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""scripts/anonymise-siteintel-recordings.py — leak gate and replacements, with synthetic words only."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "anonymise-siteintel-recordings.py"
spec = importlib.util.spec_from_file_location("anonymise", SCRIPT)
anonymise = importlib.util.module_from_spec(spec)
spec.loader.exec_module(anonymise)


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, check=False)


def recording(root: Path, body: str) -> Path:
    path = root / "psi" / "example-shop-1.test.desktop.json"
    path.parent.mkdir(parents=True)
    path.write_text(body, encoding="utf-8")
    return root


def verify(tmp_path: Path, body: str) -> subprocess.CompletedProcess:
    words = tmp_path / "words.txt"
    words.write_text("zyxfoobrand\n", encoding="utf-8")
    root = recording(tmp_path / "out", body)
    return run(SCRIPT, "--verify", str(root), "--review-words-file", str(words))


def test_bare_double_colon_untouched():
    anonymiser = anonymise.Anonymiser({"shop.test": "example-shop-1.test"})
    raw = '{"css": "::-webkit-scrollbar", "time": "::", "ip": "2001:4860::8888"}'
    assert anonymiser.text(raw, "shop.test") == '{"css": "::-webkit-scrollbar", "time": "::", "ip": "2001:db8::1"}'


def test_cookie_headers_and_screenshots_dropped():
    node = {"headers": {"Cookie": "form_key=abc", "accept": "*/*"}, "final-screenshot": "x", "img": "data:image/png;"}
    assert anonymise.strip_screenshots(node) == {"headers": {"accept": "*/*"}}


def test_verify_fails_on_forbidden_word(tmp_path):
    result = verify(tmp_path, '{"title": "ZyxFooBrand shop", "url": "https://example-shop-1.test/"}')
    assert result.returncode == 1
    assert "***" in result.stderr
    assert "zyxfoobrand" not in result.stderr.lower()


def test_verify_fails_on_unmapped_host(tmp_path):
    result = verify(tmp_path, '{"url": "https://cdn.private-client.com/logo.png"}')
    assert result.returncode == 1
    assert "private-client" not in result.stderr


def test_verify_passes_on_clean_output(tmp_path):
    body = '{"url": "https://www.example-shop-1.test/", "mail": "contact@example-shop-1.test", "api": "urlscan.io"}'
    result = verify(tmp_path, body)
    assert result.returncode == 0, result.stderr


def test_label_replaced_in_title_and_path():
    anonymiser = anonymise.Anonymiser({"sklep.acmeshop.pl": "example-shop-3.test"})
    raw = '{"title": "Acmeshop | sklep", "url": "https://sklep.acmeshop.pl/video/acmeshop_v9", "fb": "/Acmeshopfb"}'
    expected = (
        '{"title": "Example Shop 3 | sklep", "url": "https://example-shop-3.test/video/example-shop-3_v9",'
        ' "fb": "/example-shop-3fb"}'
    )
    assert anonymiser.text(raw, "sklep.acmeshop.pl") == expected


def test_missing_gitleaks_symlink_exit_2(tmp_path):
    script = tmp_path / "scripts" / SCRIPT.name
    script.parent.mkdir()
    shutil.copy(SCRIPT, script)
    result = run(script, "--verify", str(recording(tmp_path / "out", "{}")))
    assert result.returncode == 2
    assert "canonical .gitleaks.toml not found — run make check" in result.stderr
