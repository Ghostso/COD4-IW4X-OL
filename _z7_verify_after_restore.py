# -*- coding: utf-8 -*-
"""Verify the restored files byte-match the backup SHA256SUMS."""
import hashlib
import os
import sys

ROOT = os.getcwd()
BACKUP = os.path.join(ROOT, "backups", "FROZEN_20261002_222802")
SUMS = os.path.join(BACKUP, "SHA256SUMS")

# Where each backup subdir lands in the live tree.
DEST = {
    "A_observer_out": os.path.join(ROOT, "restore_iips_contract_001", "observer2", "out"),
    "A_observer_src": os.path.join(ROOT, "restore_iips_contract_001", "observer2"),
    "B_launch_scripts": os.path.join(ROOT, "run_codol_001"),
    "C_driver": os.path.join(ROOT, "CODOLServer", "_mainline"),
    "D_lobby_probe": os.path.join(ROOT, "CODOLServer", "lobby_server"),
    "E_boot_chain": os.path.join(ROOT, "run_codol_001", "sandbox_datafix_20260929"),
    "F_sandbox_config": os.path.join(ROOT, "run_codol_001", "sandbox_datafix_20260929"),
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


ok = bad = missing = 0
print("verifying against %s" % SUMS)
print()
with open(SUMS, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        want, rel = line.split(None, 1)
        rel = rel.replace("/", os.sep)
        parts = rel.split(os.sep)
        sub = parts[0]
        name = os.path.join(*parts[1:]) if len(parts) > 1 else parts[0]
        sub = sub.lstrip("\\")
        base = DEST.get(sub)
        if base is None:
            print("  ?? unknown group:", rel)
            continue
        live = os.path.join(base, name)
        if not os.path.isfile(live):
            print("  MISSING  %s" % rel)
            missing += 1
            continue
        got = sha(live)
        if got == want:
            ok += 1
            print("  OK       %s" % rel)
        else:
            bad += 1
            print("  MISMATCH %s" % rel)
            print("           got  %s" % got)
            print("           want %s" % want)

print()
print("ok=%d  mismatch=%d  missing=%d" % (ok, bad, missing))
sys.exit(0 if (bad == 0 and missing == 0) else 1)
