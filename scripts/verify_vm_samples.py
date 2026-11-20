"""Verify collected archives against selections and the pinned source tree."""

from __future__ import annotations

import argparse
import collections
import json
from datetime import UTC, datetime
from pathlib import Path

from collect_vm_samples import file_hash, git_tree, inside, read_csv, validate_rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--npm-manifest", required=True, type=Path)
    parser.add_argument("--malicious-selection", required=True, type=Path)
    parser.add_argument("--datadog-repo", required=True, type=Path)
    args = parser.parse_args(argv)
    config = json.loads((args.output_dir / "collection_config.json").read_text(encoding="utf-8"))
    if file_hash(args.npm_manifest) != config["npm_manifest_sha256"]:
        raise ValueError("npm manifest differs from the collection input")
    if file_hash(args.malicious_selection) != config["malicious_selection_sha256"]:
        raise ValueError("Malicious selection differs from the collection input")
    npm, malicious = read_csv(args.npm_manifest), read_csv(args.malicious_selection)
    tree = git_tree(args.datadog_repo, config["datadog_revision"])
    validate_rows(npm, malicious, tree)
    groups = {}
    errors = []
    checksums = []
    for group, expected in (("npm_candidates", npm), ("malicious", malicious)):
        records = read_csv(args.output_dir / f"{group}_downloads.csv")
        if len(records) != len(expected):
            raise ValueError(f"{group}: record count differs from selection")
        verified, size, hashes = 0, 0, []
        for index, (record, selected) in enumerate(zip(records, expected, strict=True)):
            try:
                keys = (
                    ("path", "eco", "cat", "pkg", "ver")
                    if group == "malicious"
                    else ("sample_id", "package", "version", "artifact_filename")
                )
                if any(record[key] != selected[key] for key in keys):
                    raise ValueError("Record does not match selection")
                if record["download_status"] != "downloaded":
                    raise ValueError(record.get("download_error", "Download failed"))
                path = inside(args.output_dir / "raw", record["artifact_path"])
                digest = file_hash(path)
                if digest != record["sha256"] or path.stat().st_size != int(
                    record["archive_bytes"]
                ):
                    raise ValueError("SHA-256 or size mismatch")
                if group == "malicious":
                    if file_hash(path, git_blob=True) != tree[selected["path"]]:
                        raise ValueError("Archive differs from pinned Datadog blob")
                    signature = b"PK"
                else:
                    if digest != selected["sha256"] or record["label"] != "unknown":
                        raise ValueError("Candidate hash or unknown label changed")
                    signature = b"\x1f\x8b"
                with path.open("rb") as source:
                    if source.read(2) != signature:
                        raise ValueError("Unexpected archive signature")
                verified += 1
                size += path.stat().st_size
                hashes.append(digest)
                relative = path.relative_to(args.output_dir.resolve()).as_posix()
                checksums.append(f"{digest}  {relative}\n")
            except (ValueError, OSError, KeyError) as exc:
                errors.append({"group": group, "index": index, "error": str(exc)})
        groups[group] = {
            "selected": len(expected),
            "verified": verified,
            "archive_bytes": size,
            "duplicate_archive_count": len(hashes) - len(set(hashes)),
        }
    summary = {
        "verified_at": datetime.now(UTC).isoformat(),
        "groups": groups,
        "datadog_revision": config["datadog_revision"],
        "errors": errors,
        "malicious_by_ecosystem": dict(collections.Counter(r["eco"] for r in malicious)),
        "candidate_label": "unknown",
        "extracted_or_executed_packages": False,
    }
    (args.output_dir / "verification.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    # Never leave an old success checksum list in place after a failed verification.
    checksum_path = args.output_dir / "archive_checksums.sha256"
    if errors:
        checksum_path.unlink(missing_ok=True)
    else:
        checksum_path.write_text("".join(checksums), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
