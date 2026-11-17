"""Chon ngau nhien mau doc tu dataset Datadog: 1 phien ban moi goi."""
import subprocess, random, collections, csv, sys

repo = sys.argv[1]
n_per_eco = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
random.seed(42)  # co dinh de lan sau chon lai ra dung bo nay

files = subprocess.run(
    ["git", "-C", repo, "ls-tree", "-r", "--name-only", "HEAD", "samples/npm", "samples/pypi"],
    capture_output=True, text=True, check=True).stdout.split("\n")

by_pkg = collections.defaultdict(list)
for p in files:
    if not p.endswith(".zip"):
        continue
    parts = p.split("/")
    if len(parts) < 6:
        continue
    eco, cat, pkg, ver, fn = parts[1], parts[2], parts[3], parts[4], parts[-1]
    by_pkg[(eco, pkg)].append(dict(path=p, eco=eco, cat=cat, pkg=pkg, ver=ver, date=fn[:10]))

chosen = []
for eco in ("npm", "pypi"):
    one_each = [random.choice(v) for (e, _), v in by_pkg.items() if e == eco]
    pick = random.sample(one_each, min(n_per_eco, len(one_each)))
    chosen += pick
    print(f"{eco}: {sum(len(v) for (e,_),v in by_pkg.items() if e==eco)} mau, "
          f"{len(one_each)} goi khac nhau, chon {len(pick)}")
    print("  theo loai:", dict(collections.Counter(r["cat"] for r in pick)))
    print("  theo nam :", dict(sorted(collections.Counter(r["date"][:4] for r in pick).items())))

with open("data/processed/selected_malicious.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["path", "eco", "cat", "pkg", "ver", "date"])
    w.writeheader(); w.writerows(chosen)
with open("data/processed/selected_paths.txt", "w") as f:
    f.writelines("/" + r["path"] + "\n" for r in chosen)
print("Da ghi data/processed/selected_malicious.csv va selected_paths.txt")
