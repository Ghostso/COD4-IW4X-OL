# -*- coding: utf-8 -*-
"""找 Demonware service **表**(不是 cmp 链)。

线索: 我们已知 service 号: 6, 8, 10, 11, 12, 21(0x15), 28, 68, 71(0x47), 80, 93, 102, 0x8A。
表形态通常是一串 4 字节递增/密集的值, 或 {id, ptr} 对。

先试: 在数据区找 "71" 与 "102" 相邻或近邻的 4 字节序列。
再试: 找 {u32 id, u32 fnptr} 对, 其中 fnptr 落在 .text 区间。
"""
import struct
from pathlib import Path

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000
TEXT_LO, TEXT_HI = 0x401000, 0xC00000


def main():
    b = DUMP.read_bytes()
    print("转储 %.1f MB" % (len(b) / 1048576))

    # 方案1: 找连续的 4 字节整数数组, 其中同时包含 71 和 102
    print("\n== 找同时含 71 与 102 的 u32 数组 ==")
    found = 0
    i = 0
    n = len(b) - 4 * 40
    while i < n and found < 10:
        j = b.find(struct.pack("<I", 71), i)
        if j < 0:
            break
        # 检查前后 40 个 u32 里有没有 102
        lo = max(0, j - 4 * 20)
        hi = min(len(b), j + 4 * 20)
        window = b[lo:hi]
        if struct.pack("<I", 102) in window:
            vals = []
            for k in range(lo, min(hi, lo + 4 * 24), 4):
                if k + 4 <= len(b):
                    v = struct.unpack_from("<I", b, k)[0]
                    vals.append(v if v < 0x10000 else 0)
            if any(v == 102 for v in vals):
                print("  0x%08X 附近: %s" % (j + BASE, " ".join(str(v) for v in vals[:24])))
                found += 1
        i = j + 1

    # 方案2: {u32 id, u32 fnptr} 对, id 在 1..200, fnptr 在 .text
    print("\n== 找 {service_id, .text 函数指针} 对 ==")
    cnt = 0
    for off in range(0, len(b) - 8, 4):
        sid = struct.unpack_from("<I", b, off)[0]
        if not (1 <= sid <= 200):
            continue
        ptr = struct.unpack_from("<I", b, off + 4)[0]
        if TEXT_LO <= ptr <= TEXT_HI:
            print("  0x%08X : service=%d -> fn 0x%X" % (off + BASE, sid, ptr))
            cnt += 1
            if cnt >= 25:
                break
    print("  (共列出 %d 条)" % cnt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
