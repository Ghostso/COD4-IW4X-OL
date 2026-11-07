# -*- coding: utf-8 -*-
"""用真实 8/3 上传帧测试 save_public_profile。"""
import os
import shutil
import struct
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import lobby_server as ls


def main():
    raw = open(os.path.join(ROOT, "lobby_tasks.bin"), "rb").read()
    off = 0
    frame = None
    while off + 6 <= len(raw):
        svc = raw[off]; task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) == (8, 3):
            frame = (struct.pack("<I", len(pl) + 3)
                     + bytes([0x86, svc, 0x03, task]) + pl)
            break
    if frame is None:
        print("没有 8/3")
        return 1
    print("帧 %d 字节" % len(frame))

    d = tempfile.mkdtemp(prefix="codol_prof_")
    try:
        os.makedirs(os.path.join(d, "player_profiles"), exist_ok=True)
        ok, note = ls.save_public_profile(frame, d)
        print("结果: ok=%s note=%s" % (ok, note))
        p = os.path.join(d, "player_profiles", "public.result")
        print("写出 %d 字节 (期望 33428)"
              % (os.path.getsize(p) if os.path.exists(p) else -1))
        # 与已有的 public.result 比对结构
        cur = os.path.join(ROOT, "player_profiles", "public.result")
        if os.path.exists(cur):
            a = open(p, "rb").read() if os.path.exists(p) else b""
            b = open(cur, "rb").read()
            print("现有 %d 字节" % len(b))
            pre = 0
            for i in range(min(len(a), len(b))):
                if a[i] != b[i]:
                    break
                pre += 1
            print("公共前缀 %d 字节 (差异应仅在 blob 与 CRC)" % pre)
            if len(a) >= 34 and len(b) >= 34:
                print("  新头: %s" % a[:34].hex(" "))
                print("  旧头: %s" % b[:34].hex(" "))
            # 尾部比较
            if len(a) >= 625 and len(b) >= 625:
                print("  新尾前 8 项: %s" % [struct.unpack_from("<i", a, len(a) - 625 + i * 5 + 1)[0] for i in range(8)])
                print("  旧尾前 8 项: %s" % [struct.unpack_from("<i", b, len(b) - 625 + i * 5 + 1)[0] for i in range(8)])
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
