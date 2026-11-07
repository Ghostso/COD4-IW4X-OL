# -*- coding: utf-8 -*-
"""Fail closed when an isolated chain references mutable legacy locations."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

WORKSPACE = Path(r"D:\BaiduNetdiskDownload\使命召唤OL").resolve()
CHAIN = WORKSPACE / "CODOL_ISOLATED_SANDBOX_20261019"
TARGET = "codoMP_client_shipRetail.exe"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def reparse_points(chain: Path):
    bad = []
    for cur, dirs, files in os.walk(chain):
        p = Path(cur)
        for name in list(dirs) + list(files):
            q = p / name
            try:
                st = q.lstat()
            except OSError:
                continue
            if q.is_symlink() or getattr(st, "st_file_attributes", 0) & 0x400:
                bad.append(str(q))
        dirs[:] = [d for d in dirs if d not in {"logs", "__pycache__"}]
    return bad

def legacy_text_hits(chain: Path):
    needles = ("REF_LOBBY_KIT", "sandbox_datafix_20260929", "sandbox_repro_test_20261019")
    hits = []
    for p in chain.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".py", ".ps1", ".cmd", ".bat", ".md"}:
            continue
        if p.name == "isolation_audit.py":
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if any(n in line for n in needles):
                hits.append({"file": str(p), "line": i, "text": line.strip()[:240]})
    return hits

def clients():
    rows = []
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + TARGET, "/FO", "CSV", "/NH"],
                       capture_output=True, text=True, errors="replace")
    for line in r.stdout.splitlines():
        cols = [x.strip('"') for x in line.split('","')]
        if cols and cols[0].casefold() == TARGET.casefold():
            try:
                rows.append({"pid": int(cols[1].replace(",", "")), "exe": cols[8] if len(cols) > 8 else ""})
            except Exception:
                pass
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", default=str(CHAIN))
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    chain = Path(a.chain).resolve()
    errors = []
    required = [
        chain / "game" / TARGET,
        chain / "game" / "Ayria" / "Bootstrapper32.dll",
        chain / "game" / "Ayria" / "Plugins" / "CodolGameServer.Localnet32",
        chain / "game" / "Ayria" / "Plugins" / "Alwaysoffline.Localnet32",
        chain / "kit" / "nt10.py", chain / "kit" / "run_all.py",
        chain / "kit" / "lobby_server.py", chain / "scripts" / "start_isolated_engine.py",
    ]
    for p in required:
        if not p.is_file():
            errors.append("missing " + str(p))
    bad_links = reparse_points(chain) if chain.exists() else []
    if bad_links:
        errors.append("reparse points: %d" % len(bad_links))
    text_hits = legacy_text_hits(chain) if chain.exists() else []
    if text_hits:
        errors.append("legacy path references: %d" % len(text_hits))
    manifest = chain / "ISOLATION_MANIFEST.json"
    mismatches = []
    if manifest.is_file():
        for row in json.loads(manifest.read_text(encoding="utf-8")):
            p = chain / row["path"]
            if not p.is_file():
                mismatches.append({"path": row["path"], "reason": "missing"})
            elif sha256(p) != row["sha256"]:
                mismatches.append({"path": row["path"], "reason": "hash mismatch"})
    else:
        errors.append("missing manifest")
    if mismatches:
        errors.append("manifest mismatches: %d" % len(mismatches))
    report = {"chain": str(chain), "errors": errors, "reparse_points": bad_links,
              "legacy_path_hits": text_hits, "manifest_mismatches": mismatches,
              "clients": clients()}
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())