# -*- coding: utf-8 -*-
"""解 8/3 上传的玩家档案(zlib), 看里面的名片槽位。"""
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")


def main():
    raw = open(TASKS, "rb").read()
    off = 0
    n = 0
    while off + 6 <= len(raw):
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) != (8, 3):
            continue
        n += 1
        print("=" * 74)
        print("8/3 #%d len=%d" % (n, len(pl)))
        # 找 0x13 0x08 <u32 len> 后的 zlib
        i = 0
        while i < len(pl):
            if pl[i] == 0x13 and i + 5 <= len(pl) and pl[i + 1] == 0x08:
                blen = struct.unpack_from("<I", pl, i + 2)[0]
                blob = pl[i + 6:i + 6 + blen]
                print("  blob len=%d, 头 4 字节: %s" % (blen, blob[:4].hex()))
                for wbits in (15, -15, 31):
                    try:
                        d = zlib.decompress(blob, wbits)
                        print("  ★ zlib(wbits=%d) 解出 %d 字节" % (wbits, len(d)))
                        # 打印可打印串
                        import re
                        strs = re.findall(rb"[ -~]{5,80}", d)
                        print("  可打印串 %d 个, 前 40:" % len(strs))
                        for s in strs[:40]:
                            print("      %s" % s.decode("latin1"))
                        # 找 cardXxx
                        for kw in (b"cardTitle", b"cardIcon", b"cardBackground",
                                   b"cardNameplate", b"cardFrame", b"callSign",
                                   b"CallSign"):
                            j = d.find(kw)
                            if j >= 0:
                                print("  ★ 含 %s @0x%X" % (kw.decode(), j))
                        return 0
                    except Exception as e:
                        print("  zlib(wbits=%d) 失败: %s" % (wbits, e))
                i += 6 + blen
            else:
                i += 1
    if n == 0:
        print("lobby_tasks.bin 里没有 8/3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
