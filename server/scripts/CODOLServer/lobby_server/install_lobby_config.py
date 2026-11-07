"""Install dwauth.ini (+ optionally trust the local CA) into a game directory.

ASCII only. Non-destructive:
  - if the target file already exists it is copied to <name>.bak_<ts> first
  - nothing outside <game-dir> is touched
  - no netsh / route / DNS / firewall / adapter changes, ever

Run:
  python -X utf8 install_lobby_config.py --game-dir "<dir>" \
      --host 127.0.0.1 --port 8443 --ca ca_append.pem [--dry-run]

Writes dwauth.ini with the 7 fields WinMain (VA 0x77EE40) parses:
  1 %59s   second host to resolve (DNS stage checks this too)
  2 %hu    uint16
  3 %59s   LOBBY HOST
  4 %hu    LOBBY PORT
  5 %x     hex32
  6 %x     hex32
  7 %x     hex32
"""
import argparse
import datetime
import os
import shutil
import sys


def backup(path):
    if not os.path.exists(path):
        return None
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = path + ".bak_" + ts
    shutil.copy2(path, dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8443)
    ap.add_argument("--host2", default=None,
                    help="field 1; defaults to --host")
    ap.add_argument("--f2", type=int, default=0)
    ap.add_argument("--f5", default="0")
    ap.add_argument("--f6", default="0")
    ap.add_argument("--f7", default="0")
    ap.add_argument("--ca", default=None,
                    help="CA pem block to append to cacert.pem")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    gd = os.path.abspath(a.game_dir)
    if not os.path.isdir(gd):
        print("game dir not found: " + gd, file=sys.stderr)
        return 2
    if not os.path.exists(os.path.join(gd, "codoMP_client_shipRetail.exe")):
        print("WARN: codoMP_client_shipRetail.exe not in " + gd + " (continuing)")

    host2 = a.host2 or a.host
    body = (
        "%s\n%d\n%s\n%d\n%s\n%s\n%s\n"
        % (host2, a.f2, a.host, a.port, a.f5, a.f6, a.f7)
    )

    target = os.path.join(gd, "dwauth.ini")
    print("dwauth.ini -> " + target)
    print(body)
    if a.dry_run:
        print("(dry run, nothing written)")
        return 0

    b = backup(target)
    if b:
        print("backup: " + b)
    with open(target, "w", encoding="ascii", newline="\n") as f:
        f.write(body)
    print("wrote " + target + " (%d bytes)" % os.path.getsize(target))

    if a.ca:
        ca = os.path.abspath(a.ca)
        cacert = os.path.join(gd, "cacert.pem")
        if not os.path.exists(cacert):
            print("cacert.pem not found in game dir; skipping CA install", file=sys.stderr)
            return 1
        with open(cacert, "rb") as f:
            existing = f.read()
        with open(ca, "rb") as f:
            block = f.read()
        if b"CODOL Local Lobby CA" in existing:
            print("cacert.pem already has local lobby CA; skipping")
        else:
            b2 = backup(cacert)
            if b2:
                print("backup: " + b2)
            with open(cacert, "ab") as f:
                f.write(block)
            print("appended local CA to " + cacert)
    return 0


if __name__ == "__main__":
    sys.exit(main())
