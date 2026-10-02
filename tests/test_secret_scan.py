# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""scripts/secret_scan.py: legacy literals from fixture YAML, counts per pattern, never a printed match."""

import importlib.util
import io
import secrets
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "secret_scan.py"
spec = importlib.util.spec_from_file_location("secret_scan", SCRIPT)
secret_scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secret_scan)

FIXTURE = """\
- model: django_example.channel
  pk: 1
  fields:
    key: not-an-api-key
# --- API keys ---
- model: django_example.apikey
  pk: 7
  fields:
    channel: 1
    key: "{literal}"
"""


def test_fixture_literals_reads_only_apikey_entries(tmp_path):
    literal = secrets.token_hex(16)
    (tmp_path / "django_example.cfg.yaml").write_text(FIXTURE.format(literal=literal))
    assert secret_scan.fixture_literals(tmp_path) == {"django_example.apikey#7": literal}


def test_scan_counts_tokens_and_literals():
    token, literal = f"ent_api_{secrets.token_urlsafe(32)}", secrets.token_hex(16)
    counts = secret_scan.scan(f"{token} {literal} {literal}", {"x#1": literal})
    assert counts == {secret_scan.TOKEN_LABEL: 1, "fixture key x#1": 2}


def test_scan_ignores_a_token_prefix_alone():
    assert secret_scan.scan("prefix ent_api_Ab3d…wxyz", {}) == {secret_scan.TOKEN_LABEL: 0}


def test_report_names_labels_and_counts_only():
    literal = secrets.token_hex(16)
    lines = secret_scan.report(secret_scan.scan(literal, {"x#1": literal}))
    assert lines == ["secret_scan: ent_api_ token: 0", "secret_scan: fixture key x#1: 1"]


def test_self_test_passes():
    assert secret_scan.self_test()


def test_a_fixtures_dir_without_keys_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["secret_scan.py", "--fixtures", str(tmp_path / "missing")])
    monkeypatch.setattr("sys.stdin", io.StringIO("clean log\n"))
    assert secret_scan.main() == 2
