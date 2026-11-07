#!/usr/bin/env python3
"""Assemble the sh1x match server Docker deployment package.

    python tools/codol_package.py --out D:/dist/sh1x-server
    python tools/codol_package.py --out D:/dist/sh1x-server --link      # hardlink game files
    python tools/codol_package.py --out D:/dist/sh1x-server --skip-game # code only

Layout written to --out:

    docker-compose.yml, .env.example, README.md, MANIFEST.txt
    gameserver/   Dockerfile, entrypoint.sh, map_handoff.awk, rcon_password.sh, codol_dedrun (32-bit Linux),
                  sh1x_svr_scripts.iwd (scripts, waypoints, bot classes; git-tracked files only)
    game/         c1_keys.bin, client_shipRetail/chinese/*.ff, main/*.iwd (read-only mount)

The lobby (Demonware emulator) is not part of it: it runs independently on the
same host, and compose mounts its state directory (LOBBY_STATE_DIR). C1.exe is
not copied: c1_keys.bin carries the two regions the server needs
(tools/codol_export_c1_keys.py).

The game directory holds Activision's shipped files and their decryption key.
Keep the package private: do not push it or its images to a public registry.

SPDX-License-Identifier: AGPL-3.0-or-later
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(REPO, "tools", "package")
DEFAULT_INSTALL = r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13"

sys.path.insert(0, os.path.join(REPO, "tools"))
import codol_export_c1_keys  # noqa: E402


def git_files(root, subpath=""):
    args = ["git", "-C", root, "ls-files", "-z"]
    if subpath:
        args += ["--", subpath]
    out = subprocess.run(args, check=True, capture_output=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


PACK = "sh1x_svr_scripts.iwd"
# Tree -> path inside the pack. Collation bookkeeping is not a server file.
PACK_TREES = (("bin/home/codol_rawfiles/", "scripts/"),
              ("bin/home/main/waypoints/", "waypoints/"),
              ("bin/home/main/mp/", "mp/"))
PACK_SKIP = {"COLLATION_CONFLICTS.txt", "COLLATION_MANIFEST.json"}


def build_pack(path):
    count = 0
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for tree, prefix in PACK_TREES:
            for rel in git_files(REPO, tree.rstrip("/")):
                src = os.path.join(REPO, rel)
                if not os.path.isfile(src) or os.path.basename(rel) in PACK_SKIP:
                    continue
                info = zipfile.ZipInfo(prefix + rel[len(tree):], date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(src, "rb") as f:
                    z.writestr(info, f.read())
                count += 1
    os.replace(tmp, path)
    return count


def place(src, dst, link):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    if link:
        try:
            os.link(src, dst)
            return
        except OSError:
            pass  # different volume: fall back to a copy
    shutil.copy2(src, dst)


def copy_tracked(root, subpath, dest, strip, exclude=()):
    count = 0
    for rel in git_files(root, subpath):
        if os.path.basename(rel) in exclude:
            continue
        src = os.path.join(root, rel)
        if not os.path.isfile(src):
            continue  # tracked but deleted in the working tree
        target = rel[len(strip):] if strip and rel.startswith(strip) else rel
        place(src, os.path.join(dest, target), False)
        count += 1
    return count


def write_text(path, text, executable=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    if executable:
        os.chmod(path, 0o755)


def template(name):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="output directory (created)")
    ap.add_argument("--install", default=DEFAULT_INSTALL, help="CoDOL 1.1.1.13 install (holds C1.exe)")
    ap.add_argument("--linux-bin", default=os.path.join(REPO, "obj", "codol-linux-bin", "codol_dedrun"),
                    help="32-bit Linux server from tools/build_codol_linux.sh")
    ap.add_argument("--link", action="store_true", help="hardlink game files instead of copying (same volume only)")
    ap.add_argument("--skip-game", action="store_true", help="do not write game/ (copy it to the VPS separately)")
    a = ap.parse_args()

    install = os.path.abspath(a.install)
    out = os.path.abspath(a.out)
    manifest = []

    with open(a.linux_bin, "rb") as f:
        if f.read(4) != b"\x7fELF":
            sys.exit(f"{a.linux_bin} is not a Linux executable; run tools/build_codol_linux.sh")
    os.makedirs(out, exist_ok=True)

    # --- game server image context: binary + the server-only script pack
    gs = os.path.join(out, "gameserver")
    for sub in ("scripts", "seed"):
        shutil.rmtree(os.path.join(gs, sub), ignore_errors=True)
    for stale in ("lobby", "data"):
        if os.path.isdir(os.path.join(out, stale)):
            shutil.rmtree(os.path.join(out, stale))
    place(a.linux_bin, os.path.join(gs, "codol_dedrun"), False)
    os.chmod(os.path.join(gs, "codol_dedrun"), 0o755)
    write_text(os.path.join(gs, "Dockerfile"), template("gameserver/Dockerfile"))
    write_text(os.path.join(gs, "entrypoint.sh"), template("gameserver/entrypoint.sh"), executable=True)
    write_text(os.path.join(gs, "map_handoff.awk"), template("gameserver/map_handoff.awk"))
    write_text(os.path.join(gs, "rcon_password.sh"), template("gameserver/rcon_password.sh"), executable=True)
    n = build_pack(os.path.join(gs, PACK))
    manifest.append(f"gameserver/{PACK}: {n} files")
    manifest.append(f"gameserver/codol_dedrun sha256 {sha256(a.linux_bin)}")
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    manifest.append(f"server source: {head}")

    write_text(os.path.join(out, "docker-compose.yml"), template("docker-compose.yml"))
    write_text(os.path.join(out, ".env.example"), template("env.example"))
    write_text(os.path.join(out, "README.md"), template("README.md"))

    # --- game files
    if not a.skip_game:
        game = os.path.join(out, "game")
        keys = os.path.join(game, "c1_keys.bin")
        os.makedirs(game, exist_ok=True)
        if codol_export_c1_keys.main(["", os.path.join(install, "C1.exe"), keys]) != 0:
            sys.exit("could not export c1_keys.bin from C1.exe")
        zones = os.path.join(install, "client_shipRetail", "chinese")
        ffs = sorted(f for f in os.listdir(zones) if f.lower().endswith(".ff"))
        iwds = sorted(f for f in os.listdir(os.path.join(install, "main")) if f.lower().endswith(".iwd"))
        size = 0
        for name in ffs:
            src = os.path.join(zones, name)
            place(src, os.path.join(game, "client_shipRetail", "chinese", name), a.link)
            size += os.path.getsize(src)
        for name in iwds:
            src = os.path.join(install, "main", name)
            place(src, os.path.join(game, "main", name), a.link)
            size += os.path.getsize(src)
        manifest.append(f"game: c1_keys.bin, {len(ffs)} fastfiles, {len(iwds)} iwds, {size / 2**30:.2f} GiB")

    write_text(os.path.join(out, "MANIFEST.txt"), "\n".join(manifest) + "\n")
    print("\n".join(manifest))
    print(f"package written to {out}")


if __name__ == "__main__":
    main()
