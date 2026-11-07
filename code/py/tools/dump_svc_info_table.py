#!/usr/bin/env python3
"""完整解析 0xE4E8C0-0xE4E9B0 的 [name_ptr][flag] 服务表; 与 configs_s.info 逐项比对。"""
import struct
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data); BASE = 0x400000

lo, hi = 0xE4E8B0, 0xE4E9C0
print("=== raw 0x%X-0x%X ===" % (lo, hi))
for i in range(lo, hi, 16):
    c = data[i:i+16]
    print("  0x%08X  %-47s  %s" % (i, " ".join("%02x"%b for b in c),
          "".join(chr(b) if 32<=b<127 else "." for b in c)))

def read_cstr(va):
    off = va - BASE
    if off < 0 or off >= N: return None
    end = data.find(b"\x00", off)
    if end < 0: return None
    return data[off:end].decode("latin1")

print("\n=== 解析为 [ptr][flag] 8字节项 ===")
print("configs_s.info 顺序: none all critical non_critical eventlog friends group mail "
      "marketplace matchmaking messaging pooledstorage profiles storage tags teams "
      "tencent titleutilities reward stats")
print()
i = lo
rows = []
while i + 8 <= hi:
    ptr = struct.unpack_from("<I", data, i)[0]
    flag = struct.unpack_from("<I", data, i+4)[0]
    name = read_cstr(ptr) if BASE <= ptr < BASE+N else None
    if name and all(32 <= ord(ch) < 127 for ch in name) and len(name) < 30 and flag < 100:
        rows.append((i, ptr, name, flag))
        i += 8
        continue
    i += 4

for off, ptr, name, flag in rows:
    print("  0x%08X  name=%-16s flag=%d   ptrVA=0x%X" % (off, name, flag, ptr))
print("\n共 %d 项" % len(rows))
