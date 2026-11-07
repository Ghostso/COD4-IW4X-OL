# -*- coding: utf-8 -*-
"""EARLY_SERVER_00 manifest generator.

Walks the early-build sample tree, records relpath/size/sha256/mtime/type for
every file, and writes a CSV manifest plus a JSON summary.  Read-only: the
sample is never written to.

Usage:
    python manifest.py <root> <out_csv> [--summary <out_json>] [--exclude NAME ...]
"""
import argparse, csv, hashlib, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

CHUNK = 1 << 20

# Category by extension (lower-case, no dot)
EXT_CAT = {
    "exe": "PE-executable", "dll": "PE-library", "sys": "PE-driver", "ocx": "PE-library",
    "pdb": "debug-symbol", "map": "debug-symbol",
    "c": "source", "cpp": "source", "h": "source", "hpp": "source", "cc": "source",
    "asm": "source", "s": "source", "inc": "source", "def": "source",
    "py": "script", "pyw": "script", "cmd": "script", "bat": "script", "ps1": "script",
    "sh": "script", "lua": "script", "js": "script",
    "gsc": "game-script", "csc": "game-script", "gsh": "game-script",
    "cfg": "config", "ini": "config", "json": "config", "yml": "config", "yaml": "config",
    "toml": "config", "xml": "config", "txt": "text", "md": "doc", "rst": "doc",
    "log": "log", "dmp": "crash-dump", "db": "database", "sqlite": "database",
    "sqlite3": "database", "sql": "database",
    "ff": "game-asset", "ff2": "game-asset", "iwd": "game-archive", "ipak": "game-archive",
    "zip": "archive", "7z": "archive", "rar": "archive", "tar": "archive", "gz": "archive",
    "png": "image", "jpg": "image", "jpeg": "image", "bmp": "image", "ico": "image", "tga": "image",
    "key": "key-material", "pem": "cert-material", "crt": "cert-material", "cer": "cert-material",
    "bin": "binary-data", "dat": "binary-data", "a": "static-lib", "lib": "static-lib",
    "o": "object", "obj": "object", "res": "resource", "rc": "source",
}

def category(name):
    _, ext = os.path.splitext(name)
    ext = ext.lower().lstrip(".")
    if ext in EXT_CAT:
        return EXT_CAT[ext]
    if not ext:
        return "no-extension"
    return "other"

def sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(CHUNK)
                if not b:
                    break
                h.update(b)
        return h.hexdigest(), None
    except OSError as e:
        return "", f"{type(e).__name__}: {e}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("out_csv")
    ap.add_argument("--summary")
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("not a directory:", root); sys.exit(2)

    ex = set(n.lower() for n in args.exclude)
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in ex]
        for fn in filenames:
            if fn.lower() in ex:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            try:
                st = os.stat(full)
            except OSError:
                files.append((rel, full, -1, 0.0))
                continue
            files.append((rel, full, st.st_size, st.st_mtime))
    files.sort(key=lambda x: x[0].lower())

    t0 = time.time()
    results = {}
    def work(item):
        rel, full, size, mtime = item
        if size < 0:
            return rel, ("", "stat-failed", size, mtime)
        digest, err = sha256(full)
        return rel, (digest, err, size, mtime)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for rel, res in pool.map(work, files):
            results[rel] = res

    total_bytes = 0
    cat_counts = {}
    cat_bytes = {}
    unreadable = []
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["relpath", "size", "sha256", "mtime_utc", "ext", "category", "read_error"])
        for rel, full, size, mtime in files:
            digest, err, sz, mt = results[rel]
            _, ext = os.path.splitext(rel)
            cat = category(rel)
            if sz >= 0:
                total_bytes += sz
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
                cat_bytes[cat] = cat_bytes.get(cat, 0) + sz
            if err:
                unreadable.append({"relpath": rel, "error": err, "size": sz})
            mt_s = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mt)) if mt else ""
            w.writerow([rel, sz, digest, mt_s, ext.lower().lstrip("."), cat, err or ""])

    summary = {
        "root": root,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "total_mib": round(total_bytes / (1 << 20), 3),
        "category_file_counts": dict(sorted(cat_counts.items(), key=lambda x: -x[1])),
        "category_bytes": {k: v for k, v in sorted(cat_bytes.items(), key=lambda x: -x[1])},
        "unreadable_count": len(unreadable),
        "unreadable": unreadable,
        "elapsed_sec": round(time.time() - t0, 2),
    }
    if args.summary:
        with open(args.summary, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in summary.items() if k != "unreadable"}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
