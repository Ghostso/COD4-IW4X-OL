"""Retry the archives the previous pass could not open, using bsdtar.

bsdtar 3.5.2 (libarchive) can read .7z / .zip / .gz / .tar and (partially) .rar,
so it closes the gap left when no 7z binary was available. Read-only.
ASCII only.
"""
import collections
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_hunt_archives_result.json")
OUT = os.path.join(HERE, "_hunt_archives_tar_result.json")

TAR = os.environ.get("SystemRoot", r"C:\Windows") + r"\System32\tar.exe"


def main():
    rows = json.load(open(SRC, encoding="utf-8"))
    todo = [r for r in rows if r.get("status") != "ok"]
    print("total=%d  retry=%d" % (len(rows), len(todo)))
    by_ext = collections.Counter(
        (r["archive"].rsplit(".", 1)[-1].lower() if "." in r["archive"] else "?")
        for r in todo)
    print("by ext:", dict(by_ext))

    results = []
    hits = []
    for i, r in enumerate(todo, 1):
        path = r["archive"]
        entry = {"archive": path, "status": "missing"}
        if not os.path.exists(path):
            results.append(entry)
            continue
        try:
            p = subprocess.run([TAR, "-tf", path], capture_output=True,
                               timeout=120)
            names = p.stdout.decode("utf-8", "replace").splitlines()
            entry["status"] = "ok" if p.returncode == 0 else "fail"
            entry["rc"] = p.returncode
            entry["entries"] = len(names)
            entry["dwauth"] = [n for n in names if "dwauth" in n.lower()]
            entry["inis"] = [n for n in names if n.lower().endswith(".ini")][:40]
            if entry["dwauth"]:
                hits.append((path, entry["dwauth"]))
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = repr(e)
        results.append(entry)
        if i % 25 == 0:
            print("  ...%d/%d" % (i, len(todo)))

    json.dump(results, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    ok = sum(1 for r in results if r.get("status") == "ok")
    fail = sum(1 for r in results if r.get("status") == "fail")
    err = sum(1 for r in results if r.get("status") in ("error", "missing"))
    print("opened=%d  failed=%d  error/missing=%d" % (ok, fail, err))
    print("dwauth hits: %d" % len(hits))
    for p, n in hits:
        print("  HIT %s -> %s" % (p, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
