#!/usr/bin/env python3
"""s138_rec_fields: 6/5 应答「248 字节记录」字段图 + 18 分支跳转表 + 分派器常量。
纯静态。所有地址为 VA (VA = file_off + 0x400000)。

输出:
  A) 记录反序列化器 0xB97FF0 的读取序 (字段偏移/宽度)
  B) 记录类 vtable @0xD5A0C8 (slot0=反序列化, slot1=GetSize)
  C) 跳转表 @0x7FE980 (type 4..0x15)
  D) 分派器 0x7FE600 读到的记录内偏移
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)

def u32(a):
    o = a - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

def ins_of(va, mx=0x400):
    return list(md.disasm(d[va - VA:va - VA + mx], va))

# ---- C) jump table ----
print("=== C) 跳转表 0x7FE980 (idx=type-4) ===")
for i in range(18):
    print("  type 0x%02X -> 0x%08X" % (i + 4, u32(0x7FE980 + i * 4)))

# ---- B) record vtable ----
print("\n=== B) 记录类 vtable @0xD5A0C8 ===")
for k in range(8):
    fn = u32(0xD5A0C8 + 4 * k)
    tag = ""
    if fn == 0xB97FF0: tag = " <- 反序列化"
    if fn == 0xB97FE0: tag = " <- GetSize"
    print("  [%d] 0x%08X%s" % (k, fn, tag))
print("  GetSize 0xB97FE0 立即数 = 0x%X" % u32(0xB97FE1) )

# ---- A) deserializer field map ----
print("\n=== A) 0xB97FF0 记录反序列化: 读取序 (helper->字段/宽度) ===")
hlp = {
    0xB761E0: ("读 tag=0x08 + 4B", 4),
    0xB769A0: ("读 tag=0x0A + 8B", 8),
    0xB76A30: ("读 tag=0x10 + 串(cap)", -1),
}
lastpush = []
for x in ins_of(0xB97FF0, 0x120):
    if x.mnemonic == "push":
        lastpush.append(x.op_str)
        if len(lastpush) > 3: lastpush.pop(0)
    elif x.mnemonic == "call":
        t = x.op_str.strip()
        if t.startswith("0xb761e0") or t.startswith("0xb769a0") or t.startswith("0xb76a30"):
            name, w = hlp[int(t, 16)]
            print("  0x%08X  %-24s width=%s   pushes=%s" % (x.address, name, w, lastpush))
        lastpush = []
    elif x.mnemonic in ("mov", "lea") and "[esi" in x.op_str and x.op_str.startswith("lea"):
        pass

# ---- D) dispatcher record offsets ----
print("\n=== D) 0x7FE600 分派器读到的记录偏移 ===")
for x in ins_of(0x7FE600, 0x60):
    if x.mnemonic in ("mov", "cmp") and "edi" in x.op_str:
        print("  0x%08X  %s %s" % (x.address, x.mnemonic, x.op_str))
