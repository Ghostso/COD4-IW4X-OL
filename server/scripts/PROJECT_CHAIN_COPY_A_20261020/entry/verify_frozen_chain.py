# -*- coding: utf-8 -*-
"""Read-only integrity check for the frozen CODOL launch chain."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "REF_LOBBY_KIT"
MANIFEST = KIT / "_golden_hashes.json"
CORE = ("run_all.py", "nt10.py", "lobby_server.py", "fake_auth_tls.py",
        "codol_crypto.py", "make_local_ca.ps1")

def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()

def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad = []
    for name in CORE:
        want = data[name]; p = KIT / name
        if not p.is_file(): bad.append((name, "missing"))
        elif p.stat().st_size != want["size"]: bad.append((name, "size"))
        elif sha(p) != want["sha256"].upper(): bad.append((name, "sha256"))
    for name in ("tas_off.flag", "poke_off.flag"):
        if (KIT / name).exists(): bad.append((name, "runtime-state"))
    print(json.dumps({"ok": not bad, "failures": bad}, indent=2))
    return 0 if not bad else 2

if __name__ == "__main__":
    raise SystemExit(main())
