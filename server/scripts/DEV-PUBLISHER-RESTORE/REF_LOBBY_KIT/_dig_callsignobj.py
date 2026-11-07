# -*- coding: utf-8 -*-
"""挖 CallSignObj / isOnlyTryon 附近的字符串, 推断名片对象字段。"""
import os
import re
import struct
import sys

GAME = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
EXE = os.path.join(GAME, "codoMP_client_shipRetail.exe")
DLL = os.path.join(GAME, "codoMP_client_shipRetailBase.dll")

PAT = re.compile(rb"CallSign[A-Za-z_]*|callsign[A-Za-z_]*|"
                 rb"isOnlyTryon|Tryon[A-Za-z_]*|"
                 rb"callsignTitle|callsignIcon|callsignBackground|"
                 rb"callsignFrame|badgeTable|nameplate", re.I)


def scan(path, label):
    if not os.path.exists(path):
        print("缺 %s" % path)
        return
    b = open(path, "rb").read()
    print("=== %s (%d 字节) ===" % (label, len(b)))
    seen = set()
    for m in PAT.finditer(b):
        s = m.group(0).decode("latin1")
        if s.lower() in seen:
            continue
        seen.add(s.lower())
        # 看它前后有没有更多可打印串
        lo = max(0, m.start() - 48)
        hi = min(len(b), m.end() + 48)
        ctx = b[lo:hi]
        strs = re.findall(rb"[ -~]{3,}", ctx)
        print("  0x%08X %-28s | %s"
              % (m.start(), s, b" | ".join(strs).decode("latin1")[:150]))
    print("  共 %d 个唯一串" % len(seen))


def main():
    scan(EXE, "exe")
    scan(DLL, "Base.dll")
    return 0


if __name__ == "__main__":
    sys.exit(main())
