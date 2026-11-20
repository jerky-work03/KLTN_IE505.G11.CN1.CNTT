"""Download existing sample selections without extracting or executing packages.

Run on the isolated collection VM. See docs/vm-sample-collection.md.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

CHUNK = 1024 * 1024
ARCHIVE_LIMIT = 100 * CHUNK
MIN_FREE_BYTES = 5 * 1024**3
USER_AGENT = "kltn-sample-collector/1.0 (academic research)"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"Missing or duplicate CSV headers: {path.name}")
        return list(reader)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("Refusing to write an empty selection")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    fd, temp = tempfile.mkstemp(prefix=".manifest-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def file_hash(path: Path, *, git_blob: bool = False) -> str:
    digest = hashlib.sha1() if git_blob else hashlib.sha256()
    if git_blob:
        digest.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as source:
        while chunk := source.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def safe_parts(value: str) -> tuple[str, ...]:
    parts = value.split("/")
    if "\\" in value or ":" in value or any(p in ("", ".", "..") for p in parts):
        raise ValueError("Unsafe sample path")
    return tuple(parts)


def inside(root: Path, *parts: str) -> Path:
    root = root.resolve()
    path = root.joinpath(*parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Sample path escapes output directory")
    return path


class RegistryRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urllib.parse.urlparse(req.full_url), urllib.parse.urlparse(newurl)
        if new.scheme != "https" or new.hostname != old.hostname or new.port not in (None, 443):
            raise ValueError("Refusing cross-host or insecure redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url: str):
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"registry.npmjs.org", "raw.githubusercontent.com"}
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Unexpected download host")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.build_opener(RegistryRedirect()).open(request, timeout=60)


def transfer(url: str, target: Path, expected: str, *, git_blob: bool = False) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".sample-", suffix=".part", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            if shutil.disk_usage(target.parent).free < MIN_FREE_BYTES + ARCHIVE_LIMIT:
                raise OSError("Collection stopped to preserve 5 GiB free")
            with open_url(url) as response:
                length = response.headers.get("Content-Length")
                if length and int(length) > ARCHIVE_LIMIT:
                    raise ValueError("Archive exceeds 100 MiB limit")
                size = 0
                while chunk := response.read(CHUNK):
                    size += len(chunk)
                    if size > ARCHIVE_LIMIT:
                        raise ValueError("Archive exceeds 100 MiB limit")
                    output.write(chunk)
        partial = Path(temp)
        if file_hash(partial, git_blob=git_blob) != expected:
            raise ValueError("Downloaded archive hash mismatch")
        with partial.open("rb") as source:
            signature = source.read(2)
        if signature != (b"PK" if git_blob else b"\x1f\x8b"):
            raise ValueError("Unexpected archive signature")
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)


def git_tree(repo: Path, revision: str) -> dict[str, str]:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Datadog revision must be a full 40-character commit SHA")
    raw = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "ls-tree",
            "-r",
            "-z",
            revision,
            "--",
            "samples/npm",
            "samples/pypi",
        ],
        check=True,
        capture_output=True,
    ).stdout
    result = {}
    for item in raw.split(b"\0"):
        if item:
            header, path = item.split(b"\t", 1)
            mode, kind, sha = header.split()
            if kind == b"blob" and mode == b"100644":
                result[path.decode()] = sha.decode()
    return result


def validate_rows(npm: list[dict], malicious: list[dict], tree: dict) -> None:
    if not npm or not malicious:
        raise ValueError("Both selections must contain samples")
    targets = set()
    for row in npm:
        package_parts = safe_parts(row["package"])
        version = safe_parts(row["version"])
        filename = safe_parts(row["artifact_filename"])
        if len(version) != 1 or len(filename) != 1:
            raise ValueError("Version and artifact filename must be single path components")
        if len(package_parts) != (2 if row["package"].startswith("@") else 1):
            raise ValueError("Invalid npm package name")
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError("Every npm sample requires the existing SHA-256")
        target = (*package_parts, *version)
        if target in targets:
            raise ValueError("Duplicate npm package/version")
        targets.add(target)
    targets = set()
    for row in malicious:
        parts = safe_parts(row["path"])
        if (
            len(parts) != 6
            or parts[0] != "samples"
            or parts[1] not in ("npm", "pypi")
            or not parts[-1].endswith(".zip")
            or row["path"] not in tree
        ):
            raise ValueError("Selected archive is absent from the pinned Datadog tree")
        if tuple(row[k] for k in ("eco", "cat", "pkg", "ver")) != parts[1:5]:
            raise ValueError("Selected Datadog path disagrees with row metadata")
        if row["path"] in targets:
            raise ValueError("Duplicate Datadog archive path")
        targets.add(row["path"])


def collect(row: dict, root: Path, tree: dict | None, revision: str) -> dict:
    result = dict(row)
    is_malicious = tree is not None
    if is_malicious:
        parts = safe_parts(row["path"])
        target = inside(root, "malicious", *parts[1:])
        expected = tree[row["path"]]
        encoded = urllib.parse.quote(row["path"], safe="/")
        url = (
            "https://raw.githubusercontent.com/DataDog/"
            f"malicious-software-packages-dataset/{revision}/{encoded}"
        )
        result["git_blob_sha1"] = expected
    else:
        target = inside(
            root,
            "npm_candidates",
            *safe_parts(row["package"]),
            row["version"],
            row["artifact_filename"],
        )
        expected = row["sha256"]
        result["label"] = "unknown"
        result["label_basis"] = "Unverified candidate; independent label verification pending"
        url = None
    try:
        for attempt in range(4):
            try:
                if target.is_file() and file_hash(target, git_blob=is_malicious) == expected:
                    break
                if url is None:
                    name = urllib.parse.quote(row["package"], safe="@")
                    version = urllib.parse.quote(row["version"], safe="")
                    with open_url(f"https://registry.npmjs.org/{name}/{version}") as response:
                        body = response.read(4 * CHUNK + 1)
                    if len(body) > 4 * CHUNK:
                        raise ValueError("Registry metadata exceeds 4 MiB limit")
                    meta = json.loads(body)
                    if meta.get("name") != row["package"] or meta.get("version") != row["version"]:
                        raise ValueError("Registry package/version mismatch")
                    url = meta["dist"]["tarball"]
                    if urllib.parse.urlparse(url).hostname != "registry.npmjs.org":
                        raise ValueError("Unexpected npm tarball host")
                transfer(url, target, expected, git_blob=is_malicious)
                break
            except (urllib.error.URLError, TimeoutError):
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
        with target.open("rb") as source:
            if source.read(2) != (b"PK" if is_malicious else b"\x1f\x8b"):
                raise ValueError("Unexpected archive signature")
        result.update(
            download_status="downloaded",
            artifact_path=target.relative_to(root).as_posix(),
            archive_bytes=str(target.stat().st_size),
            sha256=file_hash(target),
            collected_at=datetime.fromtimestamp(target.stat().st_mtime, UTC).isoformat(),
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result.update(download_status="download_error", download_error=str(exc))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--npm-manifest", required=True, type=Path)
    parser.add_argument("--malicious-selection", required=True, type=Path)
    parser.add_argument("--datadog-repo", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--workers", default=4, type=int, choices=range(1, 9))
    args = parser.parse_args(argv)
    tree = git_tree(args.datadog_repo, args.revision)
    npm, malicious = read_csv(args.npm_manifest), read_csv(args.malicious_selection)
    validate_rows(npm, malicious, tree)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "datadog_revision": args.revision,
        "workers": args.workers,
        "npm_manifest_sha256": file_hash(args.npm_manifest),
        "malicious_selection_sha256": file_hash(args.malicious_selection),
        "archive_limit_bytes": ARCHIVE_LIMIT,
        "minimum_free_bytes": MIN_FREE_BYTES,
        "started_at": datetime.now(UTC).isoformat(),
    }
    config_path = args.output_dir / "collection_config.json"
    if config_path.exists():
        previous = json.loads(config_path.read_text(encoding="utf-8"))
        for key in ("datadog_revision", "npm_manifest_sha256", "malicious_selection_sha256"):
            if previous.get(key) != config[key]:
                raise ValueError("Output directory belongs to a different selection or revision")
    else:
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    failed = 0
    for group, rows, source_tree in (("npm_candidates", npm, None), ("malicious", malicious, tree)):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = [
                pool.submit(collect, row, args.output_dir / "raw", source_tree, args.revision)
                for row in rows
            ]
            for index, job in enumerate(jobs, 1):
                result = job.result()
                results.append(result)
                if result["download_status"] != "downloaded":
                    failed += 1
                if index % 100 == 0:
                    print(f"{group}: {index}/{len(rows)} processed", flush=True)
        write_csv(args.output_dir / f"{group}_downloads.csv", results)
    print(f"Selected {len(npm) + len(malicious)} archives; download errors: {failed}")
    return int(failed != 0)


if __name__ == "__main__":
    raise SystemExit(main())
