# -*- coding: utf-8 -*-
"""直接读客户端内存里的**频道表** 0xC1B8188（每项 0x28 字节）。

依据(§10): 订阅发起函数用
    lea esi,[eax+eax*4] ; lea esi,[esi*8 + 0xC1B8188]
  ⇒ idx*40 + 0xC1B8188, 每项 40 字节。
    +0x10 / +0x14 两个字段参与收发。

这份转储是进图后的, 表里应该已有真实内容。
"""
from pathlib import Path
import struct

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\RECONNECT_20261024_1445\mem\mem_000.bin")
BASE = 0x400000
TABLE = 0xC1B8188
STRIDE = 0x28
N = 12


def main():
    b = DUMP.read_bytes()
    off = TABLE - BASE
    print("频道表 0x%X (文件偏移 0x%X), 每项 0x%X 字节, 读 %d 项\n"
          % (TABLE, off, STRIDE, N))
    for i in range(N):
        p = off + i * STRIDE
        raw = b[p:p + STRIDE]
        if len(raw) < STRIDE:
            break
        vals = struct.unpack("<10I", raw)
        nonzero = sum(1 for v in vals if v)
        tag = "  <<< 非空" if nonzero else ""
        print("项 %2d @0x%08X: %s%s"
              % (i, TABLE + i * STRIDE,
                 " ".join("%08X" % v for v in vals), tag))
        # 若某个字段看起来像字符串指针, 试着解出来
        for k, v in enumerate(vals):
            if 0xD00000 <= v <= 0xF00000:
                s = b[v - BASE:v - BASE + 60].split(b"\x00")[0]
                if s and all(32 <= c < 127 for c in s):
                    print("           +0x%02X -> \"%s\"" % (k * 4, s.decode("latin1")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

