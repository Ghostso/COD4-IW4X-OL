"""Rewrite dwauth.ini to the three-line form the working document requires,
with a restorable backup.

Current (wrong) form:
    127.0.0.1 / 0 / 127.0.0.1 / 8443 / 0 / 0 / 0
Required form (CRLF):
    formal-zone-lsg.codol.qq.com 3074
    formal-zone-auth.codol.qq.com 3074
    0x03EA
"""
import os
import shutil
import sys
import time

SAND = r"run_codol_001\sandbox_datafix_20260929"
INI = os.path.join(SAND, "dwauth.ini")
SNAP = os.path.join(SAND, "_dwauth_snap")

WANT = (
    "formal-zone-lsg.codol.qq.com 3074\r\n"
    "formal-zone-auth.codol.qq.com 3074\r\n"
    "0x03EA\r\n"
)


def show():
    if not os.path.exists(INI):
        print("dwauth.ini 不存在")
        return
    print("当前内容 (%d bytes):" % os.path.getsize(INI))
    print(repr(open(INI, "rb").read()))


def apply():
    if not os.path.exists(INI):
        raise SystemExit("找不到 %s" % INI)
    os.makedirs(SNAP, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    raw = open(INI, "rb").read()
    shutil.copy2(INI, os.path.join(SNAP, "dwauth.%s.bak" % ts))
    # keep one pristine copy for `restore`
    pristine = os.path.join(SNAP, "dwauth.original")
    if not os.path.exists(pristine):
        with open(pristine, "wb") as f:
            f.write(raw)
    print("backup -> %s/dwauth.%s.bak" % (SNAP, ts))
    print("pristine -> %s (%d bytes)" % (pristine, len(raw)))

    with open(INI, "wb") as f:
        f.write(WANT.encode("ascii"))
    print()
    print("已写入:")
    print(open(INI, "rb").read().decode("ascii", "replace"))


def restore():
    src = os.path.join(SNAP, "dwauth.original")
    if not os.path.exists(src):
        raise SystemExit("没有原始备份")
    shutil.copy2(src, INI)
    print("已还原:")
    print(repr(open(INI, "rb").read()))


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "show"
    {"show": show, "apply": apply, "restore": restore}.get(
        c, lambda: print("usage: show|apply|restore"))()
