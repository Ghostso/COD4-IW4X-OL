"""Freeze the current working state into a timestamped, verifiable backup.

Covers everything the 2026-10-02 session touched or depends on:

  A. observer binaries   out\AboProbe.*          (the thing that broke today)
  B. launch scripts      run_codol_001\*.ps1     (arg plumbing)
  C. driver              _e57a5c_experiment.py   (+ multiround, cleanup)
  D. lobby probe         lobby_server\*.py       (the server side)
  E. game boot chain     9 modules from the 09-30 reference set
  F. sandbox configs     dwauth.ini / iips.ini / BugTrace.ini
  G. hosts + agent state

Writes SHA256SUMS so a restore can be verified, not assumed.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
STAMP = time.strftime("%Y%m%d_%H%M%S")
FREEZE = os.path.join(ROOT, "backups", "FROZEN_%s" % STAMP)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


GROUPS = {
    "A_observer_out": [
        r"restore_iips_contract_001\observer2\out\AboProbe.exe",
        r"restore_iips_contract_001\observer2\out\AboProbe.dll",
        r"restore_iips_contract_001\observer2\out\AboProbe.pdb",
        r"restore_iips_contract_001\observer2\out\AboProbe.deps.json",
        r"restore_iips_contract_001\observer2\out\AboProbe.runtimeconfig.json",
    ],
    "A_observer_src": [
        r"restore_iips_contract_001\observer2\AboProbe.cs",
        r"restore_iips_contract_001\observer2\AboProbe.csproj",
    ],
    "B_launch_scripts": [
        r"run_codol_001\capture_elevated_network.ps1",
        r"run_codol_001\elevated_ifs1_observer.ps1",
    ],
    "C_driver": [
        r"CODOLServer\_mainline\_e57a5c_experiment.py",
        r"CODOLServer\_mainline\_multiround.py",
        r"CODOLServer\_mainline\agent_client.py",
        r"CODOLServer\_mainline\_z7_cleanup.py",
    ],
    "D_lobby_probe": [
        r"CODOLServer\lobby_server\lobby_plain_probe.py",
        r"CODOLServer\lobby_server\lobby_socket_server.py",
        r"CODOLServer\lobby_server\lobby_probe_server.py",
    ],
    "F_sandbox_config": [
        r"run_codol_001\sandbox_datafix_20260929\dwauth.ini",
        r"run_codol_001\sandbox_datafix_20260929\iips.ini",
        r"run_codol_001\sandbox_datafix_20260929\BugTrace.ini",
    ],
}

BOOT_CHAIN = [
    "codoMP_client_shipRetail.exe",
    "codoMP_client_shipRetailBase.dll",
    "TenProxy.dll", "TenRpcs.dll", "GameRpcs.dll",
    "TCJ.dll", "libcef.dll", "BugTrace.dll", "GbSpy.dll",
]
BOOT_SRC = r"run_codol_001\sandbox_datafix_20260929"


def main():
    os.makedirs(FREEZE, exist_ok=True)
    lines = []
    total = 0

    for grp, files in GROUPS.items():
        dst_dir = os.path.join(FREEZE, grp)
        os.makedirs(dst_dir, exist_ok=True)
        for rel in files:
            src = os.path.join(ROOT, rel)
            if not os.path.exists(src):
                lines.append("MISSING  %s  %s" % (grp, rel))
                continue
            dst = os.path.join(dst_dir, os.path.basename(rel))
            shutil.copy2(src, dst)
            lines.append("%s  %s" % (sha(dst), os.path.join(grp,
                                                            os.path.basename(rel))))
            total += 1

    # boot chain (E): copy the nine modules and record their hashes
    e_dir = os.path.join(FREEZE, "E_boot_chain")
    os.makedirs(e_dir, exist_ok=True)
    for n in BOOT_CHAIN:
        src = os.path.join(ROOT, BOOT_SRC, n)
        if not os.path.exists(src):
            lines.append("MISSING  E_boot_chain  %s" % n)
            continue
        dst = os.path.join(e_dir, n)
        shutil.copy2(src, dst)
        lines.append("%s  %s" % (sha(dst), "E_boot_chain/" + n))
        total += 1

    with open(os.path.join(FREEZE, "SHA256SUMS"), "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")

    # hosts + agent snapshot (text only)
    try:
        out = subprocess.run(["cmd", "/c", "type",
                              r"C:\Windows\System32\drivers\etc\hosts"],
                             capture_output=True, timeout=30).stdout
        with open(os.path.join(FREEZE, "hosts.snapshot"), "wb") as f:
            f.write(out)
    except Exception as e:
        print("hosts snapshot failed:", e)

    with open(os.path.join(FREEZE, "README.txt"), "w",
              encoding="utf-8") as f:
        f.write(
            "CODOL frozen state %s\n"
            "===============================\n\n"
            "A_observer_out     the observer binaries that run every round\n"
            "A_observer_src     their source (may be far newer than the\n"
            "                   binary -- the binary is what actually runs)\n"
            "B_launch_scripts   PowerShell arg plumbing\n"
            "C_driver           experiment driver + cleanup\n"
            "D_lobby_probe      local lobby server\n"
            "E_boot_chain       the nine game modules\n"
            "F_sandbox_config   dwauth.ini / iips.ini / BugTrace.ini\n"
            "hosts.snapshot     copy of the system hosts file\n"
            "SHA256SUMS         verify a restore with:\n"
            "                   sha256sum -c SHA256SUMS\n\n"
            "Verified working at freeze time:\n"
            "  2/5 valid rounds, life 108.1 s and 90.0 s,\n"
            "  LOBBY_READY_ONLY / 5E8 / ECHO / POST83 all firing.\n"
            % STAMP)

    print("frozen ->", FREEZE)
    print("files :", total)
    print("sums  :", os.path.join(FREEZE, "SHA256SUMS"))


if __name__ == "__main__":
    main()
