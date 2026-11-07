"""Restore a frozen state, then verify every file against SHA256SUMS.

Usage:  python _z7_restore.py <FROZEN_dir> [--dry]

Restoring is deliberately mechanical: copy each file listed in SHA256SUMS
back to its original location, then re-hash the destination and compare.
Nothing is inferred from filenames or timestamps.
"""
import hashlib
import os
import shutil
import sys

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"

# where each frozen group belongs in the live tree
DEST = {
    "A_observer_out": r"restore_iips_contract_001\observer2\out",
    "A_observer_src": r"restore_iips_contract_001\observer2",
    "B_launch_scripts": r"run_codol_001",
    "C_driver": r"CODOLServer\_mainline",
    "D_lobby_probe": r"CODOLServer\lobby_server",
    "E_boot_chain": r"run_codol_001\sandbox_datafix_20260929",
    "F_sandbox_config": r"run_codol_001\sandbox_datafix_20260929",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    frozen = sys.argv[1]
    dry = "--dry" in sys.argv
    sums = os.path.join(frozen, "SHA256SUMS")
    if not os.path.exists(sums):
        raise SystemExit("no SHA256SUMS in %s" % frozen)

    copied = 0
    failed = 0
    for line in open(sums, encoding="ascii"):
        line = line.strip()
        if not line or line.startswith("MISSING"):
            continue
        want, rel = line.split("  ", 1)
        # the freeze wrote Windows-style separators (os.path.join), so accept
        # either form rather than assuming "/"
        rel = rel.replace("\\", "/")
        grp, name = rel.split("/", 1)
        dst_dir = os.path.join(ROOT, DEST[grp])
        src = os.path.join(frozen, grp, name)
        dst = os.path.join(dst_dir, name)

        if not os.path.exists(src):
            print("  MISSING in freeze:", rel)
            failed += 1
            continue
        if dry:
            print("  would restore %-40s -> %s" % (name, DEST[grp]))
            copied += 1
            continue
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, dst)
        got = sha(dst)
        if got == want:
            copied += 1
        else:
            print("  HASH MISMATCH after copy:", dst)
            failed += 1

    print()
    print("%s: restored %d, failed %d"
          % ("DRY RUN" if dry else "DONE", copied, failed))


if __name__ == "__main__":
    main()
