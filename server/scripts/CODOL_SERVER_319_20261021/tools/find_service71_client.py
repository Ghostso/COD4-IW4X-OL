# -*- coding: utf-8 -*-
"""在**我们自己的 3.19 客户端运行时映像**里找 service 分发逻辑。

证据载体: run_codol_001/runs/LIVE_FULLMEM_20261022/mem/mem_000.bin
  —— 230MB 运行时全内存转储, MZ 开头, 从基址 0x400000 起的线性映像(已解壳)。
  ⇒ VA - 0x400000 = 文件偏移。

思路:
  1. 先确认转储是解壳的(用已知锚点 0x46E780);
  2. 找 "InstantMessage"/"CreateRoom"/"ChannelSubscription" 这些**我们自己客户端里的**
     字符串(不是 ol-mod 的), 拿到它们的 VA;
  3. 找引用这些字符串的代码, 那就是 service 处理逻辑的落点。
"""
import re
import struct
from pathlib import Path

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000

ANCHOR_VA = 0x46E780
ANCHOR = bytes.fromhex("558BEC83E4F881ECCC000000A1")


def main():
    print("读取转储 ...")
    b = DUMP.read_bytes()
    print("  %d 字节 (%.1f MB)" % (len(b), len(b) / 1048576))

    # 1. 锚点校验
    off = ANCHOR_VA - BASE
    got = b[off:off + len(ANCHOR)]
    print("\n锚点 0x%X: %s" % (ANCHOR_VA, "吻合(已解壳)" if got == ANCHOR else "不吻合! %s" % got.hex()))

    # 2. 找关键字符串
    keys = [b"CreateRoom", b"ChannelSubscription", b"InstantMessage", b"JoinRoom",
            b"LeaveRoom", b"ChannelSubscriptionFail", b"mmstart", b"findSessions"]
    print("\n== 字符串命中 ==")
    hits = {}
    for k in keys:
        positions = []
        start = 0
        while True:
            i = b.find(k, start)
            if i < 0:
                break
            positions.append(i + BASE)
            start = i + 1
            if len(positions) >= 6:
                break
        hits[k] = positions
        print("  %-24s %d 处 %s" % (k.decode(), len(positions),
                                    " ".join("0x%X" % v for v in positions[:6])))

    # 3. 对每个字符串 VA, 找 push 它的指令(push imm32 = 68 xx xx xx xx)
    print("\n== 引用这些字符串的代码(push imm32) ==")
    for k, vas in hits.items():
        for va in vas[:3]:
            pat = b"\x68" + struct.pack("<I", va)
            refs = []
            start = 0
            while True:
                i = b.find(pat, start)
                if i < 0:
                    break
                refs.append(i + BASE)
                start = i + 1
                if len(refs) >= 5:
                    break
            if refs:
                print("  %-22s @0x%X <- %s" % (k.decode(), va,
                                               " ".join("0x%X" % r for r in refs)))
            else:
                print("  %-22s @0x%X <- (无 push 引用)" % (k.decode(), va))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
