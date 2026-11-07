#!/usr/bin/env python3
"""正确偏移: 0xA4E8C0-0xA4E9C0 (file). [name_ptr(VA)][flag] 8字节项."""
import struct
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data); BASE = 0x400000

lo, hi = 0xA4E8B0, 0xA4E9D0
print("=== raw file 0x%X-0x%X ===" % (lo, hi))
for i in range(lo, hi, 16):
    c = data[i:i+16]
    print("  0x%08X  %-47s  %s" % (i, " ".join("%02x"%b for b in c),
          "".join(chr(b) if 32<=b<127 else "." for b in c)))

def read_cstr(va):
    off = va - BASE
    if off < 0 or off >= N: return None
    end = data.find(b"\x00", off)
    if end < 0 or end-off > 40: return None
    s = data[off:end]
    if all(32 <= b < 127 for b in s) and s:
        return s.decode("latin1")
    return None

print("\n=== [ptrVA][flag] 8字节项 ===")
i = lo; rows = []
while i + 8 <= hi:
    ptr = struct.unpack_from("<I", data, i)[0]
    flag = struct.unpack_from("<I", data, i+4)[0]
    name = read_cstr(ptr)
    if name and flag < 1000:
        rows.append((i, ptr, name, flag)); i += 8; continue
    i += 4
for off, ptr, name, flag in rows:
    print("  file0x%08X  VA0x%08X  %-16s flag=%d" % (off, off+BASE, name, flag))
print("\n共 %d 项" % len(rows))
