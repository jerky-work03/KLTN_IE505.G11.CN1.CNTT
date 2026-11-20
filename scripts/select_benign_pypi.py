"""Chon va tai goi PyPI lanh tinh truc tiep tu PyPI (khong cai dat, khong giai nen).

Quy trinh (giong select_benign_npm.py, dieu chinh cho PyPI):
  1. Ung vien tu 2 nguon:
       - danh sach top ~15.000 goi PyPI theo luot tai 30 ngay (hugovk/top-pypi-packages)
         -> nhom pho bien (va trung binh neu co)
       - mau ngau nhien tu PyPI Simple Index (ten moi goi tren PyPI)
         -> nhom trung binh va it nguoi dung; luot tai lay tu pypistats.org
  2. Loc:
       - bo goi co trong dataset Datadog (manifest.json + ten thu muc samples/pypi)
       - bo goi tung co canh bao MAL- tren OSV
       - chi lay phien ban final (khong a/b/rc/dev), phat hanh trong khoang
         [--date-from, hom nay - --min-age-days], co file sdist chua bi yank
       - goi phai co lien ket repository ma nguon (GitHub/GitLab/...)
       - sdist <= 50 MB
       - (sau khi tai) GuardDog + kiem tra thu cong: lam rieng
  3. Moi goi chon ngau nhien 1 phien ban (seed co dinh de tai lap).
  4. Chia 3 nhom theo luot tai/thang: pho bien >=100k, trung binh >=1k, it <1k; moi nhom 1/3.
  5. Tai file sdist (.tar.gz/.zip) - cung dinh dang voi phan lon mau doc cua Datadog -
     kiem tra sha256 do PyPI cong bo, KHONG giai nen; chi doc danh sach ten file
     ben trong de ghi nhan co setup.py hay khong.

Chi dung thu vien chuan cua Python. Chay tu thu muc goc cua repo:
  python scripts/select_benign_pypi.py --datadog-repo <duong-dan-dataset-datadog> --n 1500
Chay lai cung lenh se tiep tuc tu cho dang do (doc cache trong data/interim/).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import random
import re
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

PYPI = "https://pypi.org"
PYPISTATS_API = "https://pypistats.org/api/packages"
OSV_API = "https://api.osv.dev/v1/query"
TOP_LISTS = (
    "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json",
    "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json",
)
USER_AGENT = "kltn-benign-sampler/1.0 (academic research)"

BUCKETS = (("popular", 100_000), ("medium", 1_000), ("small", 0))
MAX_SDIST_BYTES = 50 * 1024 * 1024
FINAL_VERSION = re.compile(r"^\d+(\.\d+)*(\.post\d+)?$")  # bo a/b/rc/dev/local version
REPO_HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "codeberg.org", "sr.ht",
              "gitee.com", "sourceforge.net")


# ----------------------------------------------------------------- HTTP

def _request(url: str, data: bytes | None = None, accept: str = "application/json",
             retries: int = 5, sleep: float = 0.15):
    """GET/POST co thu lai khi loi mang hoac 429/5xx. Tra ve bytes hoac None neu 404."""
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if data is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(retries):
        time.sleep(sleep)
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt * 3)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 3)
                continue
            raise
    return None


def get_json(url: str, data: dict | None = None, accept: str = "application/json", **kw):
    body = _request(url, json.dumps(data).encode() if data is not None else None, accept, **kw)
    return json.loads(body) if body is not None else None


def normalize(name: str) -> str:
    """Chuan hoa ten goi theo PEP 503 (Foo_Bar.baz -> foo-bar-baz)."""
    return re.sub(r"[-_.]+", "-", name).lower()


# ----------------------------------------------------------------- Lop loc

def load_datadog_names(repo: Path) -> set[str]:
    """Ten goi PyPI doc da biet: manifest.json + ten thu muc trong samples/pypi.

    Dung git show / git ls-tree nen doc duoc ca khi repo Datadog la sparse/partial clone.
    """
    out = subprocess.run(["git", "-C", str(repo), "show", "HEAD:samples/pypi/manifest.json"],
                         capture_output=True, text=True, check=True).stdout
    names = {normalize(k) for k in json.loads(out)}
    tree = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", "HEAD",
                           "samples/pypi"], capture_output=True, text=True, check=True).stdout
    for line in tree.splitlines():
        parts = line.split("/")
        if len(parts) >= 4:  # samples/pypi/<loai>/<ten-goi>/...
            names.add(normalize(parts[3]))
    return names


def is_type_stub(name: str) -> bool:
    """Goi chi chua type hint (.pyi), vi du types-requests, pandas-stubs."""
    key = normalize(name)
    return key.startswith("types-") or key.endswith("-stubs")


def osv_has_malicious(name: str) -> bool | None:
    """True neu goi tung co canh bao MAL- tren OSV; None neu khong truy van duoc."""
    try:
        res = get_json(OSV_API, {"package": {"name": name, "ecosystem": "PyPI"}})
    except Exception:
        return None
    return any(v.get("id", "").startswith("MAL-") for v in (res or {}).get("vulns", []))


def monthly_downloads(name: str, top: dict[str, int]) -> int | None:
    """Luot tai 30 ngay: lay tu danh sach top neu co, neu khong hoi pypistats.org."""
    key = normalize(name)
    if key in top:
        return top[key]
    try:
        res = get_json(f"{PYPISTATS_API}/{urllib.parse.quote(key)}/recent", sleep=0.6)
    except Exception:
        return None
    if res is None:  # pypistats chua co du lieu -> coi nhu khong ai tai
        return 0
    return (res.get("data") or {}).get("last_month")


def bucket_of(downloads: int | None) -> str:
    if downloads is None:
        return "unknown"
    for label, threshold in BUCKETS:
        if downloads >= threshold:
            return label
    return "small"


def release_time(files: list[dict]) -> dt.datetime | None:
    times = [f.get("upload_time_iso_8601") for f in files if f.get("upload_time_iso_8601")]
    if not times:
        return None
    return min(dt.datetime.fromisoformat(t) for t in times)


def pick_sdist(files: list[dict]) -> dict | None:
    sd = [f for f in files if f.get("packagetype") == "sdist" and not f.get("yanked")]
    return sd[0] if sd else None


def eligible_versions(doc: dict, date_from: dt.datetime, date_to: dt.datetime) -> list[str]:
    """Phien ban final, phat hanh trong khoang thoi gian, co sdist chua bi yank."""
    out = []
    for ver, files in (doc.get("releases") or {}).items():
        if not FINAL_VERSION.match(ver) or not files:
            continue
        if all(f.get("yanked") for f in files) or pick_sdist(files) is None:
            continue
        published = release_time(files)
        if published and date_from <= published <= date_to:
            out.append(ver)
    return sorted(out)


def repository_url(info: dict) -> str:
    """Lien ket repository ma nguon trong project_urls/home_page; '' neu khong co."""
    urls = list((info.get("project_urls") or {}).values()) + [info.get("home_page") or ""]
    for u in urls:
        if any(h in (u or "").lower() for h in REPO_HOSTS):
            return u
    return ""


# ----------------------------------------------------------------- Ung vien

def load_top_list(cache: Path) -> dict[str, int]:
    """{ten chuan hoa: luot tai 30 ngay} cua ~15.000 goi PyPI pho bien nhat."""
    if cache.exists():
        return json.loads(cache.read_text())
    for url in TOP_LISTS:
        try:
            doc = get_json(url)
        except Exception as e:
            print(f"  [canh bao] khong tai duoc {url}: {e}", file=sys.stderr)
            continue
        if doc and doc.get("rows"):
            top = {normalize(r["project"]): int(r["download_count"]) for r in doc["rows"]}
            print(f"  top-pypi-packages ({doc.get('last_update', '?')}): {len(top)} goi",
                  file=sys.stderr)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(top))
            return top
    return {}


def collect_random_names(rng: random.Random, k: int, cache: Path) -> list[str]:
    """Lay ngau nhien k ten goi tu PyPI Simple Index (danh sach moi goi tren PyPI)."""
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        doc = get_json(f"{PYPI}/simple/", accept="application/vnd.pypi.simple.v1+json")
        all_names = sorted(p["name"] for p in doc["projects"])
        print(f"  PyPI Simple Index: {len(all_names)} ten goi", file=sys.stderr)
    except Exception as e:
        print(f"  [canh bao] khong lay duoc Simple Index: {e}", file=sys.stderr)
        return []
    result = sorted(rng.sample(all_names, min(k, len(all_names))))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return result


# ----------------------------------------------------------------- Danh gia 1 goi

def evaluate(name: str, datadog: set[str], top: dict[str, int], rng: random.Random,
             date_from, date_to, use_osv: bool, full_buckets: set[str] = frozenset()) -> dict:
    """Tra ve dict co 'status' ('accepted' hoac ly do bi loai) va thong tin goi neu duoc chon."""
    if normalize(name) in datadog:
        return {"name": name, "status": "in_datadog_dataset"}
    if is_type_stub(name):  # tuong tu @types/ ben npm: chi chua file .pyi
        return {"name": name, "status": "types_only"}
    if normalize(name) in top and bucket_of(top[normalize(name)]) in full_buckets:
        return {"name": name, "status": "skip_bucket_full"}
    # Loc bang PyPI JSON truoc (nhanh, khong gioi han); pypistats cham nen hoi sau cung
    doc = get_json(f"{PYPI}/pypi/{urllib.parse.quote(name)}/json")
    if doc is None:
        return {"name": name, "status": "not_on_pypi"}
    info = doc.get("info") or {}
    name = info.get("name") or name  # ten chinh thuc tren PyPI
    versions = eligible_versions(doc, date_from, date_to)
    if not versions:
        return {"name": name, "status": "no_version_in_window"}
    repo = repository_url(info)
    if not repo:
        return {"name": name, "status": "no_repository"}
    downloads = monthly_downloads(name, top)
    bucket = bucket_of(downloads)
    if bucket == "unknown":
        return {"name": name, "status": "downloads_unknown"}
    if bucket in full_buckets:
        return {"name": name, "status": "skip_bucket_full", "bucket": bucket}
    ver = rng.choice(versions)
    files = doc["releases"][ver]
    sdist = pick_sdist(files)
    if (sdist.get("size") or 0) > MAX_SDIST_BYTES:
        return {"name": name, "status": "too_large"}
    if use_osv:
        mal = osv_has_malicious(name)
        if mal:
            return {"name": name, "status": "osv_malicious"}
        osv_checked = mal is not None
    else:
        osv_checked = False
    age = (dt.datetime.now(dt.UTC) - date_to).days
    basis = ["absent-from-datadog-dataset", f"age>={age}d", "has-repository",
             "osv-no-MAL" if osv_checked else "osv-not-checked"]
    return {
        "name": name, "status": "accepted", "version": ver,
        "published": release_time(files).date().isoformat(),
        "downloads_last_month": downloads, "bucket": bucket,
        "has_wheel": any(f.get("packagetype") == "bdist_wheel" for f in files),
        "sdist_filename": sdist["filename"], "sdist_size": sdist.get("size"),
        "sdist_url": sdist["url"], "sha256_pypi": (sdist.get("digests") or {}).get("sha256", ""),
        "repository": repo, "osv_checked": osv_checked, "label_basis": ";".join(basis),
        "metadata_collected_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }


# ----------------------------------------------------------------- Tai file

def sdist_path(root: Path, rec: dict) -> Path:
    return root / normalize(rec["name"]) / rec["version"] / Path(rec["sdist_filename"]).name


def has_setup_py(data: bytes, filename: str) -> bool | None:
    """Chi doc danh sach ten file trong archive (khong giai nen ra dia, khong chay gi)."""
    try:
        if filename.endswith(".zip"):
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        else:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
                names = tar.getnames()
    except Exception:
        return None
    # setup.py o thu muc goc cua sdist: <ten>-<phien-ban>/setup.py
    return any(n.count("/") == 1 and n.endswith("/setup.py") for n in names)


def download(rec: dict, root: Path) -> str:
    """Tai sdist, kiem tra sha256 do PyPI cong bo (cung la ma bam ghi vao manifest)."""
    path = sdist_path(root, rec)
    if path.exists():
        data = path.read_bytes()
    else:
        data = _request(rec["sdist_url"], accept="*/*")
        if data is None:
            raise RuntimeError("sdist 404")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)  # chi luu file nen, KHONG giai nen, KHONG cai dat
    sha256 = hashlib.sha256(data).hexdigest()
    if rec["sha256_pypi"] and sha256 != rec["sha256_pypi"]:
        path.unlink(missing_ok=True)
        raise RuntimeError("sai sha256")
    rec["sha256"] = sha256
    rec["has_setup_py"] = has_setup_py(data, rec["sdist_filename"])
    rec["collected_at"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    return str(path)


# ----------------------------------------------------------------- Main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datadog-repo", required=True, type=Path,
                    help="Thu muc clone dataset Datadog")
    ap.add_argument("--n", type=int, default=1500, help="So goi lanh tinh can lay")
    ap.add_argument("--date-from", default="2024-01-01",
                    help="Chi lay phien ban phat hanh tu ngay nay")
    ap.add_argument("--min-age-days", type=int, default=180,
                    help="Phien ban phai ton tai it nhat N ngay")
    ap.add_argument("--random-pool", type=int, default=30000,
                    help="So ten lay ngau nhien tu PyPI Simple Index")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-osv", action="store_true", help="Bo qua lop OSV (khong khuyen nghi)")
    ap.add_argument("--no-download", action="store_true", help="Chi chon, khong tai sdist")
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    now = dt.datetime.now(dt.UTC)
    date_from = dt.datetime.fromisoformat(args.date_from).replace(tzinfo=dt.UTC)
    date_to = now - dt.timedelta(days=args.min_age_days)
    interim, processed = args.data_dir / "interim", args.data_dir / "processed"
    raw = args.data_dir / "raw" / "benign" / "pypi"
    for d in (interim, processed, raw):
        d.mkdir(parents=True, exist_ok=True)

    print(f"Khoang phat hanh: {date_from.date()} -> {date_to.date()}", file=sys.stderr)
    datadog = load_datadog_names(args.datadog_repo)
    print(f"Dataset Datadog: {len(datadog)} goi PyPI doc da biet", file=sys.stderr)

    top = load_top_list(interim / "benign_pypi_top.json")
    rand = collect_random_names(random.Random(args.seed), args.random_pool,
                                interim / "benign_pypi_candidates_random.json")
    print(f"Ung vien: top {len(top)} + ngau nhien {len(rand)}", file=sys.stderr)
    if not top and not rand:
        print("Khong lay duoc ung vien nao (kiem tra mang).", file=sys.stderr)
        return 1
    seen, candidates = set(), []
    for n in sorted(top) + rand:
        if normalize(n) not in seen:
            seen.add(normalize(n))
            candidates.append(n)
    rng.shuffle(candidates)
    print(f"Tong ung vien: {len(candidates)}", file=sys.stderr)

    log_path = interim / "benign_pypi_evaluated.jsonl"
    done: dict[str, dict] = {}
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            r = json.loads(line)
            done[r["key"]] = r

    quota = {"popular": args.n // 3, "medium": args.n // 3}
    quota["small"] = args.n - quota["popular"] - quota["medium"]
    chosen: list[dict] = []
    count = {k: 0 for k in quota}

    with log_path.open("a") as log:
        for i, name in enumerate(candidates):
            if all(count[b] >= quota[b] for b in quota):
                break
            if i % 200 == 0:
                print(f"  da xet {i}/{len(candidates)}, da chon {len(chosen)} {count}",
                      file=sys.stderr)
            key = normalize(name)
            rec = done.get(key)
            if rec is None:
                full = {b for b in quota if count[b] >= quota[b]}
                try:
                    rec = evaluate(name, datadog, top, rng, date_from, date_to,
                                   not args.no_osv, full)
                except Exception as e:
                    rec = {"name": name, "status": f"error: {e}"}
                rec["key"] = key
                # bo qua vi nhom du / loi mang: khong ghi cache de lan sau xet lai
                if rec["status"] not in ("skip_bucket_full", "downloads_unknown") \
                        and not rec["status"].startswith("error"):
                    log.write(json.dumps(rec) + "\n")
                    log.flush()
            if rec["status"] != "accepted" or count[rec["bucket"]] >= quota[rec["bucket"]]:
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
                print(f"  da tai {j + 1}/{len(chosen)}", file=sys.stderr)

    fields = ["name", "version", "published", "downloads_last_month", "bucket", "has_wheel",
              "has_setup_py", "sdist_filename", "sdist_size", "repository", "osv_checked",
              "sdist_url", "sha256", "path", "download_error"]
    out_csv = processed / "selected_benign_pypi.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(chosen)

    manifest_fields = ["sample_id", "ecosystem", "package", "version", "artifact_filename",
                       "sha256", "source", "source_snapshot", "label", "label_basis",
                       "release_date", "discovery_date", "collected_at",
                       "metadata_collected_at", "processing_status"]
    out_manifest = processed / "benign_pypi_manifest.csv"
    with out_manifest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=manifest_fields, lineterminator="\n")
        w.writeheader()
        for r in chosen:
            if args.no_download:
                status = "selected"
            else:
                status = "download_error" if r.get("download_error") else "downloaded"
            w.writerow({
                "sample_id": f"pypi:{normalize(r['name'])}@{r['version']}", "ecosystem": "pypi",
                "package": r["name"], "version": r["version"],
                "artifact_filename": r["sdist_filename"] if r.get("path") else "",
                "sha256": r.get("sha256", ""), "source": "pypi", "source_snapshot":
                now.date().isoformat(), "label": "benign", "label_basis": r["label_basis"],
                "release_date": r["published"], "discovery_date": "",
                "collected_at": r.get("collected_at", ""),
                "metadata_collected_at": r.get("metadata_collected_at", ""),
                "processing_status": status,
            })

    reasons: dict[str, int] = {}
    for line in log_path.read_text().splitlines():
        s = json.loads(line)["status"]
        reasons[s] = reasons.get(s, 0) + 1
    years: dict[str, int] = {}
    for r in chosen:
        years[r["published"][:4]] = years.get(r["published"][:4], 0) + 1
    print("\n=== Tong ket ===")
    print(f"Da chon: {len(chosen)}/{args.n}  theo nhom: {count}")
    print(f"Theo nam phat hanh: {dict(sorted(years.items()))}")
    print(f"Co setup.py: {sum(1 for r in chosen if r.get('has_setup_py'))}")
    print(f"Ly do loai/chon (tat ca goi da xet): {reasons}")
    print(f"Tai loi: {sum(1 for r in chosen if r.get('download_error'))}")
    print(f"Da ghi {out_csv} va {out_manifest}")
    if len(chosen) < args.n:
        print("CHUA DU SO LUONG: tang --random-pool roi chay lai.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

