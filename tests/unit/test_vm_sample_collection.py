"""Offline tests: tiny synthetic bytes only; no research package execution."""

import csv
import hashlib
import importlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
collector = importlib.import_module("collect_vm_samples")
verifier = importlib.import_module("verify_vm_samples")


def sample_rows():
    npm = {
        "sample_id": "npm:@scope/demo@1.0.0",
        "package": "@scope/demo",
        "version": "1.0.0",
        "artifact_filename": "demo-1.0.0.tgz",
        "sha256": hashlib.sha256(b"\x1f\x8bsynthetic").hexdigest(),
        "label": "benign",
    }
    bad = {
        "path": "samples/npm/malicious_intent/example/1.0.0/2026-01-01-example.zip",
        "eco": "npm",
        "cat": "malicious_intent",
        "pkg": "example",
        "ver": "1.0.0",
    }
    blob = hashlib.sha1(b"blob 11\0PKsynthetic").hexdigest()
    return npm, bad, {bad["path"]: blob}


def response(body):
    result = io.BytesIO(body)
    result.headers = {"Content-Length": str(len(body))}
    return result


def test_transfer_preserves_previous_file_on_hash_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(collector.shutil, "disk_usage", lambda _: SimpleNamespace(free=10**12))
    monkeypatch.setattr(collector, "open_url", lambda _: response(b"\x1f\x8bwrong"))
    path = tmp_path / "sample.tgz"
    path.write_bytes(b"previous")
    with pytest.raises(ValueError, match="hash mismatch"):
        collector.transfer("unused", path, "a" * 64)
    assert path.read_bytes() == b"previous"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["sample.tgz"]


def test_transfer_stops_before_network_when_disk_low(tmp_path, monkeypatch):
    monkeypatch.setattr(collector.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    monkeypatch.setattr(collector, "open_url", lambda _: pytest.fail("network must not be called"))
    with pytest.raises(OSError, match="preserve"):
        collector.transfer("unused", tmp_path / "sample.tgz", "a" * 64)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("value", ["../escape", "/absolute", "a/../b", "a\\b", "C:drive", "a//b"])
def test_reject_unsafe_paths(value):
    with pytest.raises(ValueError):
        collector.safe_parts(value)


def test_symlink_escape_is_rejected(tmp_path):
    root = tmp_path / "raw"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Host cannot create symlinks")
    with pytest.raises(ValueError, match="escapes"):
        collector.inside(root, "linked", "sample")


def test_validate_selection_checks_source_and_duplicates():
    npm, bad, tree = sample_rows()
    collector.validate_rows([npm], [bad], tree)
    with pytest.raises(ValueError, match="Duplicate npm"):
        collector.validate_rows([npm, npm], [bad], tree)
    with pytest.raises(ValueError, match="absent"):
        collector.validate_rows([npm], [bad], {})


def test_npm_label_is_unknown_and_valid_archive_resumes_without_network(tmp_path, monkeypatch):
    npm, _, _ = sample_rows()
    path = tmp_path / "npm_candidates/@scope/demo/1.0.0/demo-1.0.0.tgz"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\x1f\x8bsynthetic")
    monkeypatch.setattr(collector, "open_url", lambda _: pytest.fail("valid file must be reused"))
    result = collector.collect(npm, tmp_path, None, "a" * 40)
    assert result["download_status"] == "downloaded"
    assert result["label"] == "unknown"
    assert not Path(result["artifact_path"]).is_absolute()


def test_failed_archive_retry_replaces_only_after_verification(tmp_path, monkeypatch):
    _, bad, tree = sample_rows()
    path = tmp_path / "malicious" / Path(bad["path"]).relative_to("samples")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"partial")
    monkeypatch.setattr(collector.shutil, "disk_usage", lambda _: SimpleNamespace(free=10**12))
    monkeypatch.setattr(collector, "open_url", lambda _: response(b"PKsynthetic"))
    result = collector.collect(bad, tmp_path, tree, "a" * 40)
    assert result["download_status"] == "downloaded"
    assert path.read_bytes() == b"PKsynthetic"


@pytest.mark.parametrize(
    "url",
    ["http://registry.npmjs.org/a", "https://evil.invalid/a", "https://registry.npmjs.org:8443/a"],
)
def test_unexpected_hosts_rejected_without_network(url):
    with pytest.raises(ValueError, match="Unexpected download host"):
        collector.open_url(url)


def test_config_pins_selection_and_verifier_detects_tampering(tmp_path, monkeypatch):
    npm, bad, tree = sample_rows()
    npm_path, bad_path = tmp_path / "npm.csv", tmp_path / "bad.csv"
    collector.write_csv(npm_path, [npm])
    collector.write_csv(bad_path, [bad])
    monkeypatch.setattr(collector, "git_tree", lambda *_: tree)
    monkeypatch.setattr(verifier, "git_tree", lambda *_: tree)
    monkeypatch.setattr(collector.shutil, "disk_usage", lambda _: SimpleNamespace(free=10**12))
    meta = {
        "name": npm["package"],
        "version": npm["version"],
        "dist": {"tarball": "https://registry.npmjs.org/demo.tgz"},
    }

    def open_fake(url):
        if "raw.githubusercontent.com" in url:
            return response(b"PKsynthetic")
        if url.endswith(".tgz"):
            return response(b"\x1f\x8bsynthetic")
        return response(json.dumps(meta).encode())

    monkeypatch.setattr(collector, "open_url", open_fake)
    out = tmp_path / "output"
    common = [
        "--npm-manifest",
        str(npm_path),
        "--malicious-selection",
        str(bad_path),
        "--datadog-repo",
        str(tmp_path),
        "--output-dir",
        str(out),
    ]
    assert collector.main([*common, "--revision", "a" * 40]) == 0
    assert verifier.main(common) == 0
    with (out / "npm_candidates_downloads.csv").open(encoding="utf-8", newline="") as stream:
        record = next(csv.DictReader(stream))
    (out / "raw" / record["artifact_path"]).write_bytes(b"tampered")
    assert verifier.main(common) == 1
    assert not (out / "archive_checksums.sha256").exists()
    npm["version"] = "2.0.0"
    collector.write_csv(npm_path, [npm])
    with pytest.raises(ValueError, match="different selection"):
        collector.main([*common, "--revision", "a" * 40])
