# -*- coding: utf-8 -*-
"""EARLY_SERVER_00_HASH_VERIFY -- re-verify a tree against a Phase-0 manifest.

Read-only.  Exits 0 when every file matches, 1 when any mismatch is found.

    python EARLY_SERVER_00_HASH_VERIFY.py <manifest.csv> [--root <tree>]
"""
import argparse, csv, hashlib, os, sys

CHUNK = 1 << 20

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--root", required=True,
                    help="tree the manifest relpaths are relative to")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    rows = []
    with open(args.manifest, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    ok = changed = missing = extra_err = 0
    problems = []
    seen = set()
    for r in rows:
        rel = r["relpath"]; seen.add(rel.replace("\\", "/").lower())
        full = os.path.join(root, rel)
        want = r["sha256"]
        if not os.path.exists(full):
            missing += 1; problems.append(("MISSING", rel, want, "")); continue
        try:
            got = sha256(full)
        except OSError as e:
            extra_err += 1; problems.append(("ERROR", rel, want, str(e))); continue
        if got == want:
            ok += 1
        else:
            changed += 1; problems.append(("CHANGED", rel, want, got))

    # detect files present now but absent from manifest
    extras = []
    for dp, dn, fn in os.walk(root):
        for name in fn:
            rel = os.path.relpath(os.path.join(dp, name), root).replace("\\", "/")
            if rel.lower() not in seen:
                extras.append(rel)

    print(f"manifest entries : {len(rows)}")
    print(f"  ok             : {ok}")
    print(f"  changed        : {changed}")
    print(f"  missing        : {missing}")
    print(f"  read errors    : {extra_err}")
    print(f"  new/extra files: {len(extras)}")
    for kind, rel, want, got in problems[:50]:
        print(f"  [{kind}] {rel}")
    for rel in extras[:50]:
        print(f"  [NEW] {rel}")
    sys.exit(0 if (changed == 0 and missing == 0 and extra_err == 0 and not extras) else 1)

if __name__ == "__main__":
    main()
