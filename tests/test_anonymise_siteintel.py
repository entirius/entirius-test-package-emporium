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
    for name in ("psi/example-shop-1.test.desktop.json", "urlscan/example-shop-1.test.submit.json"):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("{}", encoding="utf-8")
    (root / "urlscan" / "example-shop-1.test.result.json").write_text(body, encoding="utf-8")
    return root


def verify_dir(tmp_path: Path, root: Path) -> subprocess.CompletedProcess:
    words = tmp_path / "words.txt"
    words.write_text("zyxfoobrand\n", encoding="utf-8")
    return run(SCRIPT, "--verify", str(root), "--review-words-file", str(words))


def verify(tmp_path: Path, body: str) -> subprocess.CompletedProcess:
    return verify_dir(tmp_path, recording(tmp_path / "out", body))


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


def test_verify_fails_on_unlisted_tld_host(tmp_path):
    for n, host in enumerate(("cdn.private-client.fr", "private-client.store", "shop.online")):
        result = verify(tmp_path / str(n), f'{{"text": "see {host} today"}}')
        assert result.returncode == 1, host
        assert host not in result.stderr


def test_verify_fails_on_ip_after_path_segment(tmp_path):
    result = verify(tmp_path, '{"url": "https://example-shop-1.test/host/203.0.113.9"}')
    assert result.returncode == 1
    assert "203.0.113.9" not in result.stderr


def test_verify_fails_on_ipv6(tmp_path):
    result = verify(tmp_path, '{"remote": "host/2a00:1450:4001:82a::200e"}')
    assert result.returncode == 1
    assert "2a00" not in result.stderr


def test_verify_fails_on_glued_label(tmp_path):
    result = verify(tmp_path, '{"fb": "/zyxfoobrandfb", "shop": "zyxfoobrandshop"}')
    assert result.returncode == 1
    assert result.stderr.count("LEAK") == 2
    assert "zyxfoobrand" not in result.stderr.lower()


def test_verify_flags_code_object_prefixed_host_in_json_value(tmp_path):
    result = verify(tmp_path, '{"host": "p.acme-probe-shop.pl", "nav": "nav.acme-probe-shop.com"}')
    assert result.returncode == 1
    assert result.stderr.count("LEAK") == 2


def test_verify_flags_code_object_prefixed_host_in_html(tmp_path):
    root = recording(tmp_path / "out", "{}")
    page = root / "sites" / "good" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text('<p>see nav.acme-probe-shop.com</p><a href="/">a.acme-probe-shop.pl</a>', encoding="utf-8")
    result = verify_dir(tmp_path, root)
    assert result.returncode == 1
    assert result.stderr.count("LEAK") == 2


def test_verify_flags_host_followed_by_equals(tmp_path):
    result = verify(tmp_path, '{"q": "acme-probe-shop.pl=1"}')
    assert result.returncode == 1
    assert "acme-probe-shop" not in result.stderr


def test_verify_finds_word_inside_long_alphanumeric_token(tmp_path):
    token = "Q7" * 70 + "zyxfoobrand" + "k3" * 49
    result = verify(tmp_path, f'{{"token": "{token}"}}')
    assert result.returncode == 1
    assert "zyxfoobrand" not in result.stderr.lower()


def test_rules_with_nested_or_missing_groups_do_not_crash(tmp_path):
    names = "(?x)(?:^|[^a-z0-9])(zyxfoo(brand|mark)|qwvbar)(?:[^a-z0-9]|$)"
    body = '{"fb": "/zyxfoobrandfb", "parent": "zyxparentwordx"}'
    result = run_with_rules(tmp_path, names, "(?x)zyxparentword", body)
    assert result.returncode == 1, result.stderr
    assert result.stderr.count("LEAK") == 2
    assert "zyx" not in result.stderr.lower()


def test_uncompilable_rule_exit_2_with_rule_id(tmp_path):
    result = run_with_rules(tmp_path, "(?x)(zyxfoo(brand", "(?x)zyxparentword", "{}")
    assert result.returncode == 2
    assert "gitleaks rule forbidden-names does not compile" in result.stderr
    assert "zyx" not in result.stderr.lower()


def run_with_rules(tmp_path: Path, names: str, parent: str, body: str) -> subprocess.CompletedProcess:
    script = tmp_path / "scripts" / SCRIPT.name
    script.parent.mkdir()
    shutil.copy(SCRIPT, script)
    rules = f"[[rules]]\nid = 'forbidden-names'\nregex = '''{names}'''\n"
    rules += f"[[rules]]\nid = 'entirius-parent-brand'\nregex = '''{parent}'''\n"
    (tmp_path / ".gitleaks.toml").write_text(rules, encoding="utf-8")
    return run(script, "--verify", str(recording(tmp_path / "out", body)))


def test_verify_wrong_level_fails(tmp_path):
    recording(tmp_path / "fixtures" / "siteintel", "{}")
    result = verify_dir(tmp_path, tmp_path / "fixtures")
    assert result.returncode == 1
    assert "not a recordings root" in result.stderr


def test_verify_empty_dir_fails(tmp_path):
    (tmp_path / "empty").mkdir()
    assert verify_dir(tmp_path, tmp_path / "empty").returncode == 1


def test_verify_scans_sites_html(tmp_path):
    root = recording(tmp_path / "out", "{}")
    page = root / "sites" / "good" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text("<title>ZyxFooBrand</title>", encoding="utf-8")
    result = verify_dir(tmp_path, root)
    assert result.returncode == 1
    assert "sites/good/index.html:1:" in result.stderr


def test_verify_passes_on_clean_output(tmp_path):
    blob = "A" * 150 + "zyxfoobrand" + "B" * 99
    body = (
        '{"url": "https://www.example-shop-1.test/main.js", "mail": "contact@example-shop-1.test", "api": "urlscan.io",'
        ' "ips": "192.0.2.7 127.0.0.1 2001:db8::1 ::1", "code": "window.config", "js": "Array.prototype.map(f)",'
        f' "css": "div.item > a.thumbnail", "query": "?v=1&sst.adr=2", "blob": "{blob}"}}'
    )
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
