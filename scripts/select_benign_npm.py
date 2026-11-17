
"""Chon va tai goi npm lanh tinh truc tiep tu registry (khong cai dat, khong giai nen).

Quy trinh:
  1. Lay danh sach ung vien tu 2 nguon:
       - npm search API (nhieu tu khoa; thien ve goi pho bien)
       - mau ngau nhien tu goi du lieu `all-the-package-names` (danh sach ten moi goi npm;
         phan lon la goi it nguoi dung) de du nhom goi nho
  2. Loc 5 lop:
       - bo goi co trong manifest.json cua Datadog (goi doc da biet)
       - bo goi tung co canh bao MAL- tren OSV
       - chi lay phien ban phat hanh trong khoang [--date-from, hom nay - --min-age-days],
         van con tren registry, khong phai prerelease, khong bi deprecated
       - goi phai co repository
       - (sau khi tai) chay GuardDog va kiem tra thu cong goi bi bao rui ro cao: lam rieng
  3. Moi goi chon ngau nhien 1 phien ban (seed co dinh de tai lap).
  4. Chia 3 nhom theo luot tai/thang: pho bien, trung binh, it -> moi nhom 1/3 so luong.
  5. Tai file .tgz tu dist.tarball, kiem tra integrity (sha512), KHONG giai nen.

Chi dung thu vien chuan cua Python. Chay tu thu muc goc cua repo:
  python scripts/select_benign_npm.py --datadog-repo <duong-dan-dataset-datadog> --n 1500
Chay lai cung lenh se tiep tuc tu cho dang do (doc cache trong data/interim/).
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import hashlib
import io
import json
import random
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REGISTRY = "https://registry.npmjs.org"
DOWNLOADS_API = "https://api.npmjs.org/downloads/point/last-month"
OSV_API = "https://api.osv.dev/v1/query"
USER_AGENT = "kltn-benign-sampler/1.0 (academic research)"

# Tu khoa tim kiem: phu nhieu loai thu vien thuong gap tren npm
DEFAULT_QUERIES = [
    "util", "cli", "react", "vue", "angular", "express", "middleware", "logger", "parser",
    "config", "string", "array", "date", "http", "request", "stream", "file", "path",
    "test", "mock", "lint", "format", "color", "markdown", "json", "yaml", "csv",
    "crypto", "hash", "uuid", "cache", "queue", "event", "promise", "async", "math",
    "validation", "schema", "router", "server", "client", "api", "sdk", "plugin",
    "webpack", "vite", "babel", "eslint", "typescript", "node", "browser", "dom",
    "image", "svg", "chart", "i18n", "auth", "jwt", "database", "sql", "mongo", "redis",
]

# Nguong luot tai/thang de chia nhom
BUCKETS = (("popular", 100_000), ("medium", 1_000), ("small", 0))
MAX_UNPACKED_BYTES = 50 * 1024 * 1024  # bo goi qua lon (>50 MB) de tiet kiem dung luong


# ----------------------------------------------------------------- HTTP

def _request(url: str, data: bytes | None = None, retries: int = 4, sleep: float = 0.15):
    """GET/POST co thu lai khi loi mang hoac 429/5xx. Tra ve bytes hoac None neu 404."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(retries):
        time.sleep(sleep)
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise
    return None


def get_json(url: str, data: dict | None = None):
    body = _request(url, json.dumps(data).encode() if data is not None else None)
    return json.loads(body) if body is not None else None


def registry_url(name: str) -> str:
    # Goi co scope (@scope/name) phai ma hoa dau "/" thanh %2F
    return f"{REGISTRY}/{urllib.parse.quote(name, safe='@')}"


# ----------------------------------------------------------------- Lop loc

def load_datadog_manifest(repo: Path) -> dict:
    """Doc samples/npm/manifest.json tu repo Datadog (git show doc duoc ca khi dung sparse checkout)."""
    out = subprocess.run(["git", "-C", str(repo), "show", "HEAD:samples/npm/manifest.json"],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def osv_has_malicious(name: str) -> bool | None:
    """True neu goi tung co canh bao MAL- tren OSV; None neu khong truy van duoc."""
    try:
        res = get_json(OSV_API, {"package": {"name": name, "ecosystem": "npm"}})
    except Exception:
        return None
    vulns = (res or {}).get("vulns", [])
    return any(v.get("id", "").startswith("MAL-") for v in vulns)


def monthly_downloads(name: str) -> int | None:
    try:
        res = get_json(f"{DOWNLOADS_API}/{urllib.parse.quote(name, safe='@')}")
    except Exception:
        return None
    return (res or {}).get("downloads")


def bucket_of(downloads: int | None) -> str:
    if downloads is None:
        return "unknown"
    for label, threshold in BUCKETS:
        if downloads >= threshold:
            return label
    return "small"


def eligible_versions(doc: dict, date_from: dt.datetime, date_to: dt.datetime) -> list[str]:
    """Phien ban phat hanh trong khoang thoi gian, khong prerelease, khong deprecated."""
    times, versions = doc.get("time", {}), doc.get("versions", {})
    out = []
    for ver, meta in versions.items():
        if "-" in ver or ver == "0.0.1-security" or meta.get("deprecated"):
            continue
        ts = times.get(ver)
        if not ts:
            continue
        published = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if date_from <= published <= date_to:
            out.append(ver)
    return sorted(out)


def has_repository(doc: dict, meta: dict) -> bool:
    repo = meta.get("repository") or doc.get("repository")
    if isinstance(repo, dict):
        repo = repo.get("url")
    return bool(repo)


# ----------------------------------------------------------------- Ung vien

def collect_candidates(queries: list[str], per_query: int, cache: Path) -> list[str]:
    if cache.exists():
        return json.loads(cache.read_text())
    names: set[str] = set()
    for q in queries:
        # 2 luot: xep hang mac dinh (thien ve pho bien) va popularity=0 (lay them goi it nguoi dung)
        for extra in ("", "&popularity=0.0&quality=0.5&maintenance=0.5"):
            for start in range(0, per_query, 250):
                url = f"{REGISTRY}/-/v1/search?text={urllib.parse.quote(q)}&size=250&from={start}{extra}"
                try:
                    res = get_json(url) or {}
                except Exception as e:
                    print(f"  [canh bao] search '{q}' loi: {e}", file=sys.stderr)
                    break
                objs = res.get("objects", [])
                names.update(o["package"]["name"] for o in objs if "package" in o)
                if len(objs) < 250:
                    break
        print(f"  tim '{q}': tong {len(names)} ung vien", file=sys.stderr)
    result = sorted(names)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return result


def collect_small_candidates(rng: random.Random, k: int, cache: Path) -> list[str]:
    """Lay ngau nhien k ten goi tu goi du lieu all-the-package-names.

    Chi doc file names.json trong bo nho (khong giai nen ra dia, khong cai dat).
    """
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        doc = get_json(registry_url("all-the-package-names"))
        latest = doc["dist-tags"]["latest"]
        dist = doc["versions"][latest]["dist"]
        data = _request(dist["tarball"])
        if data is None or not verify(data, dist.get("integrity", ""), dist.get("shasum", "")):
            raise RuntimeError("khong tai duoc hoac sai integrity")
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            member = next(m for m in tar.getmembers() if m.name.endswith("names.json"))
            all_names = json.load(tar.extractfile(member))
        print(f"  all-the-package-names {latest}: {len(all_names)} ten goi", file=sys.stderr)
    except Exception as e:
        print(f"  [canh bao] khong lay duoc all-the-package-names: {e}", file=sys.stderr)
        return []
    result = sorted(rng.sample(all_names, min(k, len(all_names))))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return result


# ----------------------------------------------------------------- Danh gia 1 goi

def evaluate(name: str, manifest: dict, rng: random.Random, date_from, date_to, use_osv: bool,
             full_buckets: set[str] = frozenset()) -> dict:
    """Tra ve dict co 'status' ('accepted' hoac ly do bi loai) va thong tin goi neu duoc chon."""
    if name in manifest:
        return {"name": name, "status": "in_datadog_manifest"}
    if name.startswith("@types/"):
        return {"name": name, "status": "types_only"}
    # Xem luot tai truoc (1 request nhe): nhom da du thi bo qua, khong tai thong tin chi tiet
    downloads = monthly_downloads(name)
    bucket = bucket_of(downloads)
    if bucket in full_buckets:
        return {"name": name, "status": "skip_bucket_full", "bucket": bucket}
    doc = get_json(registry_url(name))
    if doc is None:
        return {"name": name, "status": "not_on_registry"}
    versions = eligible_versions(doc, date_from, date_to)
    if not versions:
        return {"name": name, "status": "no_version_in_window"}
    ver = rng.choice(versions)
    meta = doc["versions"][ver]
    if not has_repository(doc, meta):
        return {"name": name, "status": "no_repository"}
    dist = meta.get("dist", {})
    if not dist.get("tarball"):
        return {"name": name, "status": "no_tarball"}
    if (dist.get("unpackedSize") or 0) > MAX_UNPACKED_BYTES:
        return {"name": name, "status": "too_large"}
    if use_osv:
        mal = osv_has_malicious(name)
        if mal:
            return {"name": name, "status": "osv_malicious"}
        osv_checked = mal is not None
    else:
        osv_checked = False
    scripts = meta.get("scripts", {}) or {}
    basis = ["absent-from-datadog-manifest", f"age>={(dt.datetime.now(dt.timezone.utc) - date_to).days}d",
             "has-repository", "osv-no-MAL" if osv_checked else "osv-not-checked"]
    return {
        "name": name, "status": "accepted", "version": ver,
        "published": doc["time"][ver][:10],
        "downloads_last_month": downloads, "bucket": bucket,
        "has_install_script": any(k in scripts for k in ("preinstall", "install", "postinstall")),
        "unpacked_size": dist.get("unpackedSize"),
        "tarball_url": dist["tarball"], "integrity": dist.get("integrity", ""),
        "shasum": dist.get("shasum", ""), "osv_checked": osv_checked,
        "label_basis": ";".join(basis),
        "metadata_collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }


# ----------------------------------------------------------------- Tai file

def verify(data: bytes, integrity: str, shasum: str) -> bool:
    if integrity.startswith("sha512-"):
        return base64.b64encode(hashlib.sha512(data).digest()).decode() == integrity[7:]
    if shasum:
        return hashlib.sha1(data).hexdigest() == shasum
    return True


def tarball_path(root: Path, name: str, ver: str) -> Path:
    safe = name.replace("/", "__")
    return root / safe / ver / f"{safe}-{ver}.tgz"


def download(rec: dict, root: Path) -> str:
    """Tai .tgz, kiem tra sha512 cua npm, tinh them sha256 theo hop dong du lieu cua nhom."""
    path = tarball_path(root, rec["name"], rec["version"])
    if path.exists():
        data = path.read_bytes()
    else:
        data = _request(rec["tarball_url"])
        if data is None:
            raise RuntimeError("tarball 404")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)  # chi luu file nen, KHONG giai nen, KHONG cai dat
    if not verify(data, rec["integrity"], rec["shasum"]):
        path.unlink(missing_ok=True)
        raise RuntimeError("sai integrity")
    rec["sha256"] = hashlib.sha256(data).hexdigest()
    rec["collected_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return str(path)


# ----------------------------------------------------------------- Main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datadog-repo", required=True, type=Path, help="Thu muc clone dataset Datadog")
    ap.add_argument("--n", type=int, default=1500, help="So goi lanh tinh can lay")
    ap.add_argument("--date-from", default="2024-01-01", help="Chi lay phien ban phat hanh tu ngay nay")
    ap.add_argument("--min-age-days", type=int, default=180, help="Phien ban phai ton tai it nhat N ngay")
    ap.add_argument("--per-query", type=int, default=500, help="So ket qua search toi da moi tu khoa/luot")
    ap.add_argument("--small-pool", type=int, default=30000,
                    help="So ten lay ngau nhien tu all-the-package-names (0 = khong dung nguon nay)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-osv", action="store_true", help="Bo qua lop kiem tra OSV (khong khuyen nghi)")
    ap.add_argument("--no-download", action="store_true", help="Chi chon, khong tai file .tgz")
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    now = dt.datetime.now(dt.timezone.utc)
    date_from = dt.datetime.fromisoformat(args.date_from).replace(tzinfo=dt.timezone.utc)
    date_to = now - dt.timedelta(days=args.min_age_days)
    interim, processed = args.data_dir / "interim", args.data_dir / "processed"
    raw = args.data_dir / "raw" / "benign" / "npm"
    for d in (interim, processed, raw):
        d.mkdir(parents=True, exist_ok=True)

    print(f"Khoang phat hanh: {date_from.date()} -> {date_to.date()}", file=sys.stderr)
    manifest = load_datadog_manifest(args.datadog_repo)
    print(f"Manifest Datadog: {len(manifest)} goi doc da biet", file=sys.stderr)

    candidates = collect_candidates(DEFAULT_QUERIES, args.per_query, interim / "benign_candidates.json")
    print(f"Ung vien tu search: {len(candidates)}", file=sys.stderr)
    if args.small_pool > 0:
        small = collect_small_candidates(random.Random(args.seed), args.small_pool,
                                         interim / "benign_candidates_small.json")
        print(f"Ung vien tu all-the-package-names: {len(small)}", file=sys.stderr)
        candidates = sorted(set(candidates) | set(small))
    rng.shuffle(candidates)
    print(f"Tong ung vien: {len(candidates)}", file=sys.stderr)

    # Cache ket qua danh gia de chay lai tiep tuc duoc
    log_path = interim / "benign_evaluated.jsonl"
    done: dict[str, dict] = {}
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            r = json.loads(line)
            done[r["name"]] = r

    quota = {"popular": args.n // 3, "medium": args.n // 3}
    quota["small"] = args.n - quota["popular"] - quota["medium"]
    chosen: list[dict] = []
    count = {k: 0 for k in quota}

    with log_path.open("a") as log:
        for i, name in enumerate(candidates):
            if all(count[b] >= quota[b] for b in quota):
                break
            if i % 200 == 0:
                print(f"  da xet {i}/{len(candidates)}, da chon {len(chosen)} {count}", file=sys.stderr)
            rec = done.get(name)
            if rec is None:
                full = {b for b in quota if count[b] >= quota[b]}
                try:
                    rec = evaluate(name, manifest, rng, date_from, date_to, not args.no_osv, full)
                except Exception as e:
                    rec = {"name": name, "status": f"error: {e}"}
                if rec["status"] != "skip_bucket_full":  # goi bi bo qua vi nhom du: khong ghi cache
                    log.write(json.dumps(rec) + "\n")
                    log.flush()
            if rec["status"] != "accepted" or rec["bucket"] not in quota:
                continue
            if count[rec["bucket"]] >= quota[rec["bucket"]]:
                continue
            chosen.append(rec)
            count[rec["bucket"]] += 1

    if not args.no_download:
        for j, rec in enumerate(chosen):
            try:
                rec["path"] = download(rec, raw)
            except Exception as e:
                rec["path"] = ""
                rec["download_error"] = str(e)
            if j % 100 == 0:
                print(f"  da tai {j+1}/{len(chosen)}", file=sys.stderr)

    fields = ["name", "version", "published", "downloads_last_month", "bucket", "has_install_script",
              "unpacked_size", "osv_checked", "tarball_url", "integrity", "path", "download_error"]
    out_csv = processed / "selected_benign_npm.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(chosen)

    # Manifest theo mau data/manifests/manifest.template.csv cua nhom (chi ten, phien ban, ma bam)
    manifest_fields = ["sample_id", "ecosystem", "package", "version", "artifact_filename", "sha256",
                       "source", "source_snapshot", "label", "label_basis", "release_date",
                       "discovery_date", "collected_at", "metadata_collected_at", "processing_status"]
    snapshot = now.date().isoformat()
    out_manifest = processed / "benign_npm_manifest.csv"
    with out_manifest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=manifest_fields)
        w.writeheader()
        for r in chosen:
            if args.no_download:
                status = "selected"
            else:
                status = "download_error" if r.get("download_error") else "downloaded"
            w.writerow({
                "sample_id": f"npm:{r['name']}@{r['version']}", "ecosystem": "npm",
                "package": r["name"], "version": r["version"],
                "artifact_filename": Path(r["path"]).name if r.get("path") else "",
                "sha256": r.get("sha256", ""), "source": "npm-registry", "source_snapshot": snapshot,
                "label": "benign", "label_basis": r.get("label_basis", ""),
                "release_date": r["published"], "discovery_date": "",
                "collected_at": r.get("collected_at", ""),
                "metadata_collected_at": r.get("metadata_collected_at", ""),
                "processing_status": status,
            })

    # Tong ket de ghi vao bao cao
    reasons: dict[str, int] = {}
    for line in log_path.read_text().splitlines():
        s = json.loads(line)["status"]
        s = "error" if s.startswith("error") else s
        reasons[s] = reasons.get(s, 0) + 1
    years: dict[str, int] = {}
    for r in chosen:
        years[r["published"][:4]] = years.get(r["published"][:4], 0) + 1
    print("\n=== Tong ket ===")
    print(f"Da chon: {len(chosen)}/{args.n}  theo nhom: {count}")
    print(f"Theo nam phat hanh: {dict(sorted(years.items()))}")
    print(f"Co script cai dat: {sum(r['has_install_script'] for r in chosen)}")
    print(f"Ly do loai/chon (tat ca goi da xet): {reasons}")
    print(f"Tai loi: {sum(1 for r in chosen if r.get('download_error'))}")
    print(f"Da ghi {out_csv} va {out_manifest}")
    if len(chosen) < args.n:
        print("CHUA DU SO LUONG: tang --per-query hoac them tu khoa roi chay lai.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
