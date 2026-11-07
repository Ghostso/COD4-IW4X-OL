"""RESTORE-IIPS-CONTRACT-002 - sandbox builder.

Builds one isolated experiment sandbox per matrix cell. The real installation
("COD OL") is only ever READ. Every sandbox is a directory of junctions
back into the real install, except IIPS, which is a real directory so the
provider DLL (and optionally IFS.dll) can be substituted without touching the
installation.

Cells (normal token only; the elevated arm is out of scope this round):
    orig_noifs    Original shipped iips.dll, IFS.dll absent
    orig_ifs      Original shipped iips.dll, IFS.dll present
    lrm_noifs     LocalRM_v3.dll as iips.dll, IFS.dll absent
    lrm_ifs       LocalRM_v3.dll as iips.dll, IFS.dll present

The "IFS present" condition is exactly the round-001 single-factor change:
IIPS\\IFS2.dll is exposed under the name IFS.dll.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
ROUND = os.path.join(ROOT, "restore_iips_contract_002")
SBXROOT = os.path.join(ROUND, "sandbox")
ORIGINAL_IIPS = os.path.join(GAME, "IIPS", "iips.dll")
LOCALRM_V3 = os.path.join(ROOT, "LocalRM_v3.dll")
IFS2 = os.path.join(GAME, "IIPS", "IFS2.dll")

ORIGINAL_SHA = "E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770"
LOCALRM_V3_SHA = "032FAC66A3F78027AA93A7EDB6B1506693C15EE9AAD1896F7BE9AE3D21A3EF26"
IFS2_SHA = "5B0324E0B2BA3545A6C02626287D4FBC6A3116594744F4647333982D85508421"

CELLS = {
    "orig_noifs": ("original", False),
    "orig_ifs": ("original", True),
    "lrm_noifs": ("localrm_v3", False),
    "lrm_ifs": ("localrm_v3", True),
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()


def rmdir_junction_safe(path):
    resolved = os.path.realpath(path)
    base = os.path.realpath(SBXROOT)
    if not resolved.startswith(base + os.sep):
        raise SystemExit("refusing to remove %s (outside %s)" % (resolved, base))
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", path], capture_output=True)


def build(cell):
    provider, ifs_present = CELLS[cell]
    sbx = os.path.join(SBXROOT, cell)
    if os.path.isdir(sbx):
        rmdir_junction_safe(sbx)
    os.makedirs(os.path.join(sbx, "IIPS"), exist_ok=True)

    for e in os.listdir(GAME):
        if e == "IIPS":
            continue
        s = os.path.join(GAME, e)
        d = os.path.join(sbx, e)
        if os.path.isdir(s):
            subprocess.run(["cmd", "/c", "mklink", "/J", d, s], capture_output=True)
        else:
            subprocess.run(["cmd", "/c", "mklink", "/H", d, s], capture_output=True)

    src_iips = os.path.join(GAME, "IIPS")
    dst_iips = os.path.join(sbx, "IIPS")
    for e in os.listdir(src_iips):
        s = os.path.join(src_iips, e)
        d = os.path.join(dst_iips, e)
        if os.path.isdir(s):
            subprocess.run(["cmd", "/c", "mklink", "/J", d, s], capture_output=True)
        else:
            if e.lower() in ("iips.dll", "ifs.dll"):
                continue
            shutil.copy2(s, d)

    if provider == "original":
        shutil.copy2(ORIGINAL_IIPS, os.path.join(dst_iips, "iips.dll"))
    else:
        shutil.copy2(LOCALRM_V3, os.path.join(dst_iips, "iips.dll"))

    if ifs_present:
        shutil.copy2(IFS2, os.path.join(dst_iips, "IFS.dll"))

    info = {
        "cell": cell,
        "sandbox": sbx,
        "provider": provider,
        "ifs_present": ifs_present,
        "iips_dll": {"size": os.path.getsize(os.path.join(dst_iips, "iips.dll")),
                     "sha256": sha(os.path.join(dst_iips, "iips.dll"))},
        "ifs_dll": ({"size": os.path.getsize(os.path.join(dst_iips, "IFS.dll")),
                     "sha256": sha(os.path.join(dst_iips, "IFS.dll")),
                     "source": "IIPS\\IFS2.dll"} if ifs_present else None),
    }
    # integrity of the real installation
    info["install_iips_sha256"] = sha(ORIGINAL_IIPS)
    info["install_iips_is_original"] = (info["install_iips_sha256"] == ORIGINAL_SHA)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True, choices=sorted(CELLS))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    info = build(a.cell)
    if a.json:
        print(json.dumps(info, indent=2))
    else:
        print("built %s  provider=%s ifs_present=%s" % (a.cell, info["provider"], info["ifs_present"]))
        print("  iips.dll sha256 = %s" % info["iips_dll"]["sha256"])
        if info["ifs_dll"]:
            print("  IFS.dll  sha256 = %s" % info["ifs_dll"]["sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
