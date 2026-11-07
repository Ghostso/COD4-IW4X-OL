# -*- coding: utf-8 -*-
"""Build a physically independent CODOL local-engine sandbox."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

WORKSPACE = Path(r"D:\BaiduNetdiskDownload\使命召唤OL").resolve()
SOURCE_GAME = WORKSPACE / "COD OL"
SOURCE_KIT = WORKSPACE / "CODOL_LOCAL_ENGINE_CHAIN_20261019" / "kit"
SOURCE_SCRIPTS = WORKSPACE / "CODOL_LOCAL_ENGINE_CHAIN_20261019" / "scripts"
CHAIN = WORKSPACE / "CODOL_ISOLATED_SANDBOX_20261019"

ROOT_DIRS = ["components", "Cross", "DirectX", "locales", "main", "Microsoft.VC90.CRT",
             "miles", "scripts", "TCLS", "TGuard", "tqm", "WeGameLauncher"]
AYRIA_DIRS = ["Assets", "Plugins"]
IIPS_DIRS = ["config", "Snapshot", "Tenio", "TPFUI", "vodcache"]
IIPS_FILE_DENY = {"HostPid", "Progress.ini"}
KIT_FILES = [
    "nt10.py", "run_all.py", "lobby_server.py", "fake_auth_tls.py", "codol_crypto.py",
    "make_local_ca.ps1", "write_dwauth.py", "local_native_server.py", "battle_server.py",
    "battle_selftest.py", "marketplace_store.py", "marketplace-catalog-merged.json",
    "marketplace-inventory.json", "player-account.json", "firingrange-gamestate.bin",
    "firingrange-session.enabled", "push_seq_offset.txt", "ready_push.on", "tas_spec.txt",
    "lobby_spec.txt", "late_spec.txt", "patch_spec.txt", "coop_map.txt", "secrets.txt",
    "battle_security_key.txt", "public-tail-items.txt", "marketplace-catalog-client.json",
    "marketplace-catalog.json", "marketplace-catalog-client.on", "marketplace-catalog-merged.on",
    "marketplace-currency-lenient.on", "playlists-include-pve.on", "catalog-include-sku-table.on",
    "keepalive.on",
    # TLS auth is a hard startup dependency; keep the complete generated set
    # with every physically independent kit.
    "_rsa.txt", "_leaf2.cer", "_ca.pem", "_ca.cer",
    "_leaf2.key", "_leaf2_chain.pem",
]
SCRIPT_FILES = ["native_engine_attach.py", "native_engine_bootstrap.py", "round2_dump_and_reverse.py"]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def check_space(required: int):
    probe = WORKSPACE
    free = shutil.disk_usage(probe).free
    reserve = 2 * 1024**3
    if free < required + reserve:
        raise SystemExit("insufficient free space: need %.2f GiB + 2 GiB reserve, have %.2f GiB" %
                         (required / 1024**3, free / 1024**3))

def copy_file(src: Path, dst: Path, records):
    if not src.is_file():
        return False
    if dst.exists():
        raise SystemExit("refusing to overwrite: " + str(dst))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    records.append({"path": dst.relative_to(CHAIN).as_posix(),
                    "source": str(src), "size": dst.stat().st_size,
                    "sha256": sha256(dst)})
    return True

def copy_tree(src: Path, dst: Path, records, skip_names=()):
    if not src.is_dir():
        return
    for cur, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in set(skip_names)]
        target_dir = dst / Path(cur).relative_to(src)
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in files:
            if name in set(skip_names):
                continue
            s = Path(cur) / name
            if s.is_symlink():
                raise SystemExit("source link forbidden: " + str(s))
            copy_file(s, target_dir / name, records)

def estimate():
    total = 0
    for p in SOURCE_GAME.iterdir():
        if p.is_file():
            total += p.stat().st_size
    for name in ROOT_DIRS + ["Ayria"]:
        p = SOURCE_GAME / name
        total += sum(x.stat().st_size for x in p.rglob("*") if x.is_file())
    iips = SOURCE_GAME / "IIPS"
    total += sum(x.stat().st_size for x in iips.iterdir() if x.is_file())
    for name in IIPS_DIRS:
        total += sum(x.stat().st_size for x in (iips / name).rglob("*") if x.is_file())
    return total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()
    needed = estimate()
    print("planned bytes=%d (%.2f GiB)" % (needed, needed / 1024**3))
    if a.plan:
        return 0
    if CHAIN.exists() and any(CHAIN.iterdir()):
        raise SystemExit("refusing to write nonempty target: " + str(CHAIN))
    check_space(needed)
    CHAIN.mkdir(parents=True, exist_ok=True)
    for d in ("game", "game/Ayria/Logs", "game/Logs", "game/players",
              "game/TenproxyLog", "game/TimeLog", "game/IIPS", "kit", "scripts",
              "logs", "state", "tmp"):
        (CHAIN / d).mkdir(parents=True, exist_ok=True)
    records = []
    for src in SOURCE_GAME.iterdir():
        if src.is_file():
            copy_file(src, CHAIN / "game" / src.name, records)
    for name in ROOT_DIRS:
        copy_tree(SOURCE_GAME / name, CHAIN / "game" / name, records)
    for name in AYRIA_DIRS:
        copy_tree(SOURCE_GAME / "Ayria" / name, CHAIN / "game" / "Ayria" / name, records)
    for name in ("Bootstrapper32.dll", "Injector32.exe", "ol_room_owner.exe"):
        copy_file(SOURCE_GAME / "Ayria" / name, CHAIN / "game" / "Ayria" / name, records)
    for src in (SOURCE_GAME / "IIPS").iterdir():
        if src.is_file() and src.name not in IIPS_FILE_DENY:
            copy_file(src, CHAIN / "game" / "IIPS" / src.name, records)
    for name in IIPS_DIRS:
        copy_tree(SOURCE_GAME / "IIPS" / name, CHAIN / "game" / "IIPS" / name, records)
    for name in KIT_FILES:
        copy_file(SOURCE_KIT / name, CHAIN / "kit" / name, records)
    for name in SCRIPT_FILES + ["start_local_engine.py", "isolation_audit.py"]:
        copy_file(SOURCE_SCRIPTS / name, CHAIN / "scripts" / name, records)
    manifest = CHAIN / "ISOLATION_MANIFEST.json"
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"chain": str(CHAIN), "files": len(records),
                      "bytes": sum(r["size"] for r in records),
                      "manifest": str(manifest)}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
