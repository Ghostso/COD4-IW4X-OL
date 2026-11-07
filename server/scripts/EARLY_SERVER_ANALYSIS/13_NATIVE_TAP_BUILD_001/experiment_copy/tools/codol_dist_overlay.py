#!/usr/bin/env python3
"""Build the sh1x match server distribution in CoDOL install layout.

    python tools/codol_dist_overlay.py --out "D:/CoD/CODOL Builds/sh1x Server 1.1.1.13"

    codol_dedrun.exe, codol_dedrun         Windows and 32-bit Linux servers
    START-SH1X-SERVER.cmd, start-sh1x-server.sh, README-SH1X-SERVER.txt
    c1_keys.bin                            archive keys (the server's stand-in for C1.exe)
    client_shipRetail/chinese/*.ff         the shipped fastfiles
    main/*.iwd                             the shipped archives
    main/sh1x_svr_scripts.iwd              scripts/<GSC + rawfile tree>, waypoints/, mp/botclasstable.csv
    main/server.cfg                        loose settings (kept if it already exists)

The lobby is not included: it runs separately on the same host (server.cfg
points at its state directory). The script pack is a plain zip; "_svr_" in its
name keeps it out of every archive list sent to clients (sv_iwds, the pure list,
referenced archives). Only git-tracked server files go into it.

Game files are hardlinked when the output shares a volume with the install
(--copy forces copies). Keep the result private: it carries Activision's
content and its decryption key.

SPDX-License-Identifier: AGPL-3.0-or-later
"""
import argparse
import os
import secrets
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codol_export_c1_keys  # noqa: E402
import codol_package as pkg  # noqa: E402

REPO = pkg.REPO
DIST = os.path.join(REPO, "tools", "dist")
PACK = pkg.PACK
# Earlier layouts of this folder; removed so only the current one remains.
STALE = ("home", "scripts", "codol_map_handoff.ps1", "CODOL")


def write_text(path, text, crlf):
    text = text.replace("\r\n", "\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", "\r\n") if crlf else text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--install", default=pkg.DEFAULT_INSTALL)
    ap.add_argument("--windows-bin", default=os.path.join(REPO, "bin", "codol_dedrun.exe"))
    ap.add_argument("--linux-bin", default=os.path.join(REPO, "obj", "codol-linux-bin", "codol_dedrun"))
    ap.add_argument("--copy", action="store_true", help="copy game files instead of hardlinking")
    ap.add_argument("--lobby-state", default=os.path.join(pkg.DEFAULT_INSTALL, "CODOL", "1.1.1.13_server", "alpha0022"),
                    help="the separately run lobby's state directory, for a new server.cfg ('' = placeholders)")
    a = ap.parse_args()

    install = os.path.abspath(a.install)
    out = os.path.abspath(a.out)
    if os.path.commonpath([out, install]) == install:
        sys.exit("--out must not be inside the install it is built from")
    with open(a.windows_bin, "rb") as f:
        if f.read(2) != b"MZ":
            sys.exit(f"{a.windows_bin} is not a Windows executable")
    with open(a.linux_bin, "rb") as f:
        if f.read(4) != b"\x7fELF":
            sys.exit(f"{a.linux_bin} is not a Linux executable (tools/build_codol_linux.sh)")
    os.makedirs(os.path.join(out, "main"), exist_ok=True)
    notes = []

    for name in STALE:
        p = os.path.join(out, name)
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.isfile(p):
            os.remove(p)

    # --- game files at their install paths
    if codol_export_c1_keys.main(["", os.path.join(install, "C1.exe"), os.path.join(out, "c1_keys.bin")]):
        sys.exit("could not export c1_keys.bin")
    size = 0
    zones = os.path.join(install, "client_shipRetail", "chinese")
    ffs = sorted(f for f in os.listdir(zones) if f.lower().endswith(".ff"))
    for name in ffs:
        pkg.place(os.path.join(zones, name), os.path.join(out, "client_shipRetail", "chinese", name), not a.copy)
        size += os.path.getsize(os.path.join(zones, name))
    iwds = sorted(f for f in os.listdir(os.path.join(install, "main")) if f.lower().endswith(".iwd"))
    for name in iwds:
        pkg.place(os.path.join(install, "main", name), os.path.join(out, "main", name), not a.copy)
        size += os.path.getsize(os.path.join(install, "main", name))
    notes.append(f"game files: c1_keys.bin, {len(ffs)} fastfiles, {len(iwds)} iwds ({size / 2**30:.2f} GiB)")

    # --- server
    pkg.place(a.windows_bin, os.path.join(out, "codol_dedrun.exe"), False)
    pkg.place(a.linux_bin, os.path.join(out, "codol_dedrun"), False)
    os.chmod(os.path.join(out, "codol_dedrun"), 0o755)
    with open(os.path.join(DIST, "START-SH1X-SERVER.cmd"), encoding="utf-8") as f:
        write_text(os.path.join(out, "START-SH1X-SERVER.cmd"), f.read(), True)
    with open(os.path.join(DIST, "start-sh1x-server.sh"), encoding="utf-8") as f:
        write_text(os.path.join(out, "start-sh1x-server.sh"), f.read(), False)
    os.chmod(os.path.join(out, "start-sh1x-server.sh"), 0o755)
    with open(os.path.join(DIST, "sh1x-rollout.sh"), encoding="utf-8") as f:
        write_text(os.path.join(out, "sh1x-rollout.sh"), f.read(), False)
    os.chmod(os.path.join(out, "sh1x-rollout.sh"), 0o755)
    with open(os.path.join(DIST, "README-SH1X-SERVER.txt"), encoding="utf-8") as f:
        write_text(os.path.join(out, "README-SH1X-SERVER.txt"), f.read(), True)
    n = pkg.build_pack(os.path.join(out, "main", PACK))
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    notes.append(f"main/{PACK}: {n} files (server source {head})")

    cfg = os.path.join(out, "main", "server.cfg")
    if os.path.exists(cfg):
        notes.append("main/server.cfg: kept (already present)")
    else:
        with open(os.path.join(DIST, "server.cfg"), encoding="utf-8") as f:
            text = f.read()
        # Match an existing lobby: its state directory and the RCON password it
        # already sends. Otherwise leave placeholders and a fresh password.
        state = os.path.abspath(a.lobby_state) if a.lobby_state else None
        rcon_file = os.path.join(state, "native_server_rcon.txt") if state else None
        if state and os.path.isdir(state):
            s = state.replace("\\", "/")
            text = (text.replace('"lobby_state/securitykey.bin"', f'"{s}/securitykey.bin"')
                        .replace('"lobby_state/game_admissions.txt"', f'"{s}/game_admissions.txt"')
                        .replace('"lobby_state/resources"', f'"{s}/resources"'))
            notes.append(f"main/server.cfg: lobby state directory {s}")
        else:
            notes.append("main/server.cfg: lobby paths are placeholders -- edit the codol_*Path lines")
        if rcon_file and os.path.isfile(rcon_file):
            with open(rcon_file, encoding="ascii") as f:
                text = text.replace("__RCON_PASSWORD__", f.read().strip())
            notes.append("main/server.cfg: rcon_password taken from the lobby")
        else:
            text = text.replace("__RCON_PASSWORD__", secrets.token_hex(16))
            notes.append("main/server.cfg: new random rcon_password -- give the lobby the same one")
        write_text(cfg, text, True)
    print("\n".join(notes))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
