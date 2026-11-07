#!/usr/bin/env python3
"""全文件搜 push imm32 / mov reg,imm32 指向服务名串区; 以及 cmp imm,102。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
BASE = 0x400000
LO, HI = BASE + 0x6CC900, BASE + 0x6CD200

def s_at(va):
    off = va - BASE
    e = data.find(b"\x00", off)
    if e < 0 or e - off > 60:
        return None
    try:
        return data[off:e].decode("ascii")
    except Exception:
        return None

print("=== push imm32 -> 串区 ===")
n = 0
for i in range(len(data) - 5):
    if data[i] == 0x68:
        v = struct.unpack_from("<I", data, i + 1)[0]
        if LO <= v <= HI:
            s = s_at(v)
            if s:
                print("  file 0x%06X VA 0x%08X push -> %r" % (i, i + BASE, s))
                n += 1
print("  共", n)

print("\n=== mov reg,imm32 -> 串区 ===")
n = 0
for i in range(len(data) - 5):
    if 0xB8 <= data[i] <= 0xBF:
        v = struct.unpack_from("<I", data, i + 1)[0]
        if LO <= v <= HI:
            s = s_at(v)
            if s:
                print("  file 0x%06X VA 0x%08X mov -> %r" % (i, i + BASE, s))
                n += 1
print("  共", n)

print("\n=== cmp r32, 102 ===")
n = 0
for i in range(len(data) - 6):
    b, m = data[i], data[i+1]
    if b == 0x81 and (m & 0xF8) == 0xF8:
        v = struct.unpack_from("<I", data, i + 2)[0]
        if v in (102, 21, 80, 93, 4, 9, 10, 11, 28, 68, 71, 8, 3, 6, 29):
            print("  cmp r32,%d @file 0x%06X VA 0x%08X" % (v, i, i + BASE))
            n += 1
    if b == 0x83 and (m & 0xF8) == 0xF8:
        v = data[i+2]
        if v in (102, 21, 80, 93):
            print("  cmp r32,%d(short) @file 0x%06X VA 0x%08X" % (v, i, i + BASE))
            n += 1
print("  共", n)
