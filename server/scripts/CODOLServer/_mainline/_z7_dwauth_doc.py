"""Write dwauth.ini in the exact 7-field form from DWAUTH_ORIGIN_FINAL.md,
which is the authoritative analysis of the [100] popup.

Field map proven by disassembly of WinMain 0x77EE40:
    1  %59s -> 0x81A7F34   second host to resolve
    2  %hu  -> 0x81A9780   uint16
    3  %59s -> 0x81A76A8   LOBBY HOST
    4  %hu  -> 0x81A9EC4   LOBBY PORT
    5  %x   -> 0x81A9EB8   hex32
    6  %x   -> 0x81A56A4   hex32
    7  %x   -> 0x81A76E4   hex32

The document is explicit that 127.0.0.1 as a literal does NOT trigger DNS,
which is why it satisfies the "do not touch system networking" constraint.
"""
import os
import shutil
import sys
import time

SAND = r"run_codol_001\sandbox_datafix_20260929"
INI = os.path.join(SAND, "dwauth.ini")
SNAP = os.path.join(SAND, "_dwauth_snap")


def build(host, port):
    return (
        "%s\r\n"      # 1  second host
        "0\r\n"       # 2  uint16
        "%s\r\n"      # 3  LOBBY HOST
        "%d\r\n"      # 4  LOBBY PORT
        "0\r\n"       # 5  hex32
        "0\r\n"       # 6  hex32
        "0\r\n"       # 7  hex32
        % (host, host, port)
    )


def apply(host, port):
    if not os.path.exists(INI):
        raise SystemExit("no dwauth.ini at %s" % INI)
    os.makedirs(SNAP, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(INI, os.path.join(SNAP, "dwauth.%s.bak" % ts))
    pristine = os.path.join(SNAP, "dwauth.original")
    if not os.path.exists(pristine):
        shutil.copy2(INI, pristine)
    txt = build(host, port)
    with open(INI, "wb") as f:
        f.write(txt.encode("ascii"))
    print("backup  -> %s/dwauth.%s.bak" % (SNAP, ts))
    print("pristine-> %s" % pristine)
    print()
    print("written:")
    print(open(INI, "rb").read().decode("ascii", "replace"))


def show():
    print(repr(open(INI, "rb").read()))


def restore():
    src = os.path.join(SNAP, "dwauth.original")
    shutil.copy2(src, INI)
    print("restored:", repr(open(INI, "rb").read()))


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "show"
    if c == "show":
        show()
    elif c == "apply":
        apply(sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1",
              int(sys.argv[3]) if len(sys.argv) > 3 else 8443)
    elif c == "restore":
        restore()
