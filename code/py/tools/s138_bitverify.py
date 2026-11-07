#!/usr/bin/env python3
"""138 · 位流写入器反向验证：用真实客户端上行数据(11/4 payload)试解析。

如果我的位流模型正确，那么按 [5位code][字段] 反复切分，应该能干净地读完，
且 code 只应落在已知集合 {1,3,8,0x10,0x13,0x15,0x6b,0x6c} 里。
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CODE_NAMES = {1: "Bool", 3: "U8", 6: "U16", 7: "I32", 8: "U32", 0x0A: "U64",
              0x10: "String", 0x13: "Blob", 0x15: "Full", 0x6B: "Arr6b", 0x6C: "Arr6c"}

# 真实样本
SAMPLES = [
    # 11/4 外层是 TLV：0a <u64> 13 08 <u32 len> <blob> 08 <u32 1> 00
    # 取 blob 内部（17 字节）做位流验证
    ("11/4 #62 blob内层 17B",
     "18 1c 5a 98 d6 14 53 91 cf 01 14 da 00 00 00 00 00"),
    # 11/4 #61 的大 blob（0x8d=141 字节）
    ("11/4 #61 blob内层 141B",
     "02 04 00 00 00 30 00 00 00 e0 68 ab 5b ab 63 ab 03 00 00 00 00 98 03 00 00 "
     "f0 30 47 06 d0 06 f7 45 96 36 47 27 97 36 46 07 f0 1f c0 c0 d0 74 d3 52 84 "
     "33 65 33 c4 96 56 e6 46 07 00 00 00 e0 36 00 00 00 00 00 00 00 00 00 00 f0 0f 00"),
]


class BitReader(object):
    def __init__(self, data):
        self.d = data
        self.pos = 0

    def bits_left(self):
        return len(self.d) * 8 - self.pos

    def read(self, n):
        if n <= 0 or self.pos + n > len(self.d) * 8:
            return None
        v = 0
        for i in range(n):
            p = self.pos + i
            bit = (self.d[p >> 3] >> (7 - (p & 7))) & 1
            v = (v << 1) | bit
        self.pos += n
        return v

    def peek(self, n):
        save = self.pos
        v = self.read(n)
        self.pos = save
        return v


def parse(data, max_fields=40):
    """按 [5位code][字段] 反复切分。"""
    br = BitReader(data)
    out = []
    for _ in range(max_fields):
        if br.bits_left() < 5:
            break
        code = br.peek(5)
        if code is None:
            break
        br.read(5)
        nm = CODE_NAMES.get(code, "?0x%02X" % code)
        if code in (1,):
            v = br.read(1)
            out.append((code, nm, v))
        elif code == 3:
            v = br.read(8)
            out.append((code, nm, v))
        elif code == 6:
            v = br.read(16)
            out.append((code, nm, v))
        elif code == 7:
            v = br.read(32)
            out.append((code, nm, v if v is None or v < 2**31 else v - 2**32))
        elif code == 8:
            v = br.read(32)
            out.append((code, nm, v))
        elif code == 0x0A:
            v = br.read(64)
            out.append((code, nm, v))
        elif code == 0x10:
            # 读 NUL 结尾字符串
            s = bytearray()
            while True:
                c = br.read(8)
                if c is None or c == 0:
                    break
                s.append(c)
            out.append((code, nm, bytes(s)))
        elif code == 0x13:
            sub = br.read(5)
            if sub != 8:
                out.append((0x13, "Blob(子码=0x%02X?)" % (sub or 0), None))
                break
            ln = br.read(32)
            if ln is None or ln > len(data):
                out.append((0x13, "Blob(len=%s 异常)" % ln, None))
                break
            raw = bytearray()
            for _i in range(ln):
                c = br.read(8)
                if c is None:
                    break
                raw.append(c)
            out.append((code, "Blob(%dB)" % ln, bytes(raw)))
        elif code == 0x15:
            # 显式位置宽：紧跟 5 位宽度码
            sub = br.read(5)
            wmap = {8: 32, 3: 8, 1: 1, 6: 16, 0x0A: 64}
            w = wmap.get(sub)
            if w is None:
                out.append((0x15, "Full(未知子码0x%02X)" % (sub or 0), None))
                break
            v = br.read(w)
            out.append((code, "Full/0x%02X(%d位)" % (sub, w), v))
        else:
            out.append((code, nm, None))
            break
    return out, br.pos, len(data) * 8


if __name__ == "__main__":
    for name, hexs in SAMPLES:
        data = bytes.fromhex(hexs.replace(" ", ""))
        print("=" * 74)
        print("%s  (%d 字节 / %d 位)" % (name, len(data), len(data) * 8))
        print("  raw:", data.hex())
        fields, used, total = parse(data)
        for i, (code, nm, v) in enumerate(fields):
            sv = repr(v) if isinstance(v, (bytes,)) else v
            print("   #%-2d code=0x%02X %-14s = %s" % (i, code, nm, sv))
        print("  解析消耗 %d / %d 位 ; 剩余 %d 位" % (used, total, total - used))
        print()
