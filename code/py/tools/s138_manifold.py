#!/usr/bin/env python3
"""138 · dwRoomMessageManifold 位流模型 (逐指令还原 0x6256C0 反序列化 / 0x625520 序列化)
      + 全量语料扫描 (corpus.json)。

模型 (全部来自反汇编, 见同目录 README 段):
  读器 0xB779A0(buf, bitLen, flag=1):
      拷贝 buf → 内部缓冲;  bitpos = 0
      读 1 位 → [obj+0x21] "hasCodes"
      bitpos = 1
  0xB774E0(expCode) : 若 hasCodes==0 → 直接 true (不读); 否则读 5 位字段码并断言 == expCode
  0xB772E0(dst,nbit): MSB-first 读 nbit 位
  0xB761E0(dst)     : code(8) + 32 位
  0xB76AF0(dst,&cap) / 0x4F3EB0: code(0x13) + code(8) + 32 位 len + len*8 位数据

0x6256C0 = dwRoomMessageManifold::Deserialize(this, BitReader**):
   code(3) + u8   → this+0x4      (消息类型; ==1 表示"又是 Manifold")
   code(8) + u32  → 条数 N
   N 次:
     code(1) + 1 bit hasValue
     if hasValue: code(0x15) + 64 bit value      → node.qword
     code(0x13) + code(8) + u32 blen + blen*8 bit → 一条内嵌位流 (新 BitReader)
     节点 { reader*, qword } 追加到 this+0x8 的 list
"""
import json
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

F_BOOL, F_U8, F_U32, F_STR, F_BLOB, F_FULL, F_STRUCT = 1, 3, 8, 0x10, 0x13, 0x15, 0x17
CODE_W = 5


class BitReader(object):
    """还原 0xB779A0(flag=1) + 0xB772E0 + 0xB774E0。"""

    def __init__(self, data):
        self.buf = bytes(data)
        self.nbits = len(self.buf) * 8
        self.pos = 0
        self.has_codes = 0
        self.ok = True
        if len(self.buf):
            self.has_codes = self._bits(1)
            self.pos = 1

    def _bits(self, n):
        if self.pos + n > self.nbits:
            self.ok = False
            return 0
        v = 0
        for i in range(n):
            p = self.pos + i
            v = (v << 1) | ((self.buf[p >> 3] >> (7 - (p & 7))) & 1)
        self.pos += n
        return v

    def read_bits(self, n):
        return self._bits(n)

    def read_code(self, expect):
        """0xB774E0: 读 5 位字段码, 断言 == expect。"""
        if not self.has_codes:
            return True
        got = self._bits(CODE_W)
        return got == expect

    def read_u32(self):
        if not self.read_code(F_U32):
            return None
        return self._bits(32)

    def read_blob(self):
        """0x4F3EB0: code 0x13 + code 8 + u32 len + len*8 位。"""
        if not self.read_code(F_BLOB):
            return None
        if not self.read_code(F_U32):
            return None
        n = self._bits(32)
        if not self.ok or n > self.nbits:
            self.ok = False
            return None
        out = bytearray()
        for i in range(n):
            out.append(self._bits(8))
        return bytes(out)


# ---------------- Manifold 反序列化 (0x6256C0) ----------------
class Manifold(object):
    def __init__(self):
        self.type = 0
        self.items = []          # [(reader, qword, blob_bytes)]


def parse_manifold(rd, depth=0, max_depth=4):
    """还原 0x6256C0。rd 必须已在 bitpos=1 (hasCodes 已读)。"""
    m = Manifold()
    if not rd.read_code(F_U8):
        return None
    m.type = rd.read_bits(8)
    if not rd.ok:
        return None
    n = rd.read_u32()
    if n is None:
        return None
    if not rd.ok or n > 4096:
        return None
    for _ in range(n):
        if not rd.read_code(F_BOOL):
            return None
        has_val = rd.read_bits(1)
        if not rd.ok:
            return None
        val = 0
        if has_val:
            if not rd.read_code(F_FULL):
                return None
            val = rd.read_bits(64)
            if not rd.ok:
                return None
        blob = rd.read_blob()
        if blob is None:
            return None
        m.items.append((BitReader(blob), val, blob))
    return m


def describe(blob, depth=0, max_depth=4):
    rd = BitReader(blob)
    if not rd.read_code(F_U8):
        return "  " * depth + "(no code3)"
    t = rd.read_bits(8)
    if not rd.ok:
        return "  " * depth + "(short)"
    if t != 1:
        return "  " * depth + "dwRoomMessage type=0x%02X" % t
    # rewind to bit 1 and parse as manifold
    rd2 = BitReader(blob)
    m = parse_manifold(rd2)
    if m is None:
        return "  " * depth + "Manifold(parse FAIL)"
    lines = ["  " * depth + "Manifold type=%d items=%d" % (m.type, len(m.items))]
    for i, (r, v, bb) in enumerate(m.items):
        lines.append("  " * (depth + 1) + "[%d] u64=0x%X blob=%dB" % (i, v, len(bb)))
        if depth + 1 < max_depth:
            lines.append(describe(bb, depth + 2, max_depth))
    return "\n".join(lines)


# ---------------- 序列化 (0x625520) 对照 ----------------
def build_manifold(msg_type, items):
    """items: [(hasValue, u64, blobbytes)]"""
    bits = []

    def wb(v, n):
        for i in range(n):
            bits.append((v >> (n - 1 - i)) & 1)

    def wcode(c):
        wb(c, CODE_W)

    wb(1, 1)             # hasCodes = 1 (0xB779A0 flag)
    wcode(F_U8); wb(msg_type, 8)
    wcode(F_U32); wb(len(items), 32)
    for hasv, val, blob in items:
        wcode(F_BOOL); wb(1 if hasv else 0, 1)
        if hasv:
            wcode(F_FULL); wb(val, 64)
        wcode(F_BLOB); wcode(F_U32); wb(len(blob), 32)
        for b in blob:
            wb(b, 8)
    out = bytearray((len(bits) + 7) // 8)
    for i, b in enumerate(bits):
        if b:
            out[i >> 3] |= 1 << (7 - (i & 7))
    return bytes(out)


def build_message(msg_type, payload_builder=None):
    """一条最简 dwRoomMessage 位流: hasCodes + code3 + u8 type (+ payload)"""
    bits = []

    def wb(v, n):
        for i in range(n):
            bits.append((v >> (n - 1 - i)) & 1)
    wb(1, 1)
    wb(F_U8, CODE_W)
    wb(msg_type & 0xFF, 8)
    if payload_builder:
        payload_builder(wb, lambda c: wb(c, CODE_W))
    out = bytearray((len(bits) + 7) // 8)
    for i, b in enumerate(bits):
        if b:
            out[i >> 3] |= 1 << (7 - (i & 7))
    return bytes(out)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        d = json.load(open(sys.argv[2] if len(sys.argv) > 2
                           else "_byte_papers/corpus/corpus.json", encoding="utf-8"))
        hits = 0
        for e in d:
            b = bytes.fromhex(e["payload"])
            if len(b) < 3:
                continue
            rd = BitReader(b)
            if not rd.has_codes:
                continue
            if not rd.read_code(F_U8):
                continue
            t = rd.read_bits(8)
            if t == 1:
                print("MANIFOLD? svc=%d task=%d len=%d %s" %
                      (e["svc"], e["task"], e["len"], b[:32].hex()))
                hits += 1
        print("hits =", hits)
        sys.exit(0)

    print("=== 1. 一条最简 dwRoomMessageReady(0x10) ===")
    b = build_message(0x10, lambda wb, wc: (wc(F_BOOL), wb(1, 1)))
    print("  %s  (%d B)" % (b.hex(), len(b)))
    print("  bits: 1 | 00011 | 00010000 | 00001 | 1")

    print("\n=== 2. 最小 Manifold: type=1, 1 条, 内嵌 Ready(0x10) ===")
    inner = build_message(0x10, lambda wb, wc: (wc(F_BOOL), wb(1, 1)))
    mf = build_manifold(1, [(False, 0, inner)])
    print("  inner  = %s (%d B)" % (inner.hex(), len(inner)))
    print("  manifold = %s (%d B)" % (mf.hex(), len(mf)))
    print("  ---- 自解析 ----")
    print(describe(mf))
