#!/usr/bin/env python3
"""1) 解析 PE 节表拿到 .text 范围。
2) 在 .text 里搜 push imm32 (0x68) / mov reg,imm32 (B8-BF) 形式的引用, 目标落在服务名串区。
3) 搜 cmp ..., 0x66 (102) 与 0x15(21)/0x50(80)/0x5d(93) 附近。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
BASE = 0x400000

# PE 节表
pe = struct.unpack_from("<I", data, 0x3C)[0]
nsec = struct.unpack_from("<H", data, pe + 6)[0]
optsz = struct.unpack_from("<H", data, pe + 20)[0]
sec0 = pe + 24 + optsz
print("=== 节表 ===")
secs = []
for i in range(nsec):
    o = sec0 + i * 40
    name = data[o:o+8].rstrip(b"\x00").decode("latin1")
    vsize, va, rsize, roff = struct.unpack_from("<IIII", data, o + 8)
    print("  %-8s VA=0x%08X VSize=0x%06X Raw=0x%06X RawOff=0x%06X" % (name, va, vsize, rsize, roff))
    secs.append((name, va, vsize, roff, rsize))

def va2off(va):
    for name, sva, vsz, roff, rsz in secs:
        if sva <= va < sva + max(vsz, rsz):
            return roff + (va - sva)
    return None

text = [s for s in secs if s[0] == ".text"][0]
tva, tvsz, troff, trsz = text[1], text[2], text[3], text[4]
tdata = data[troff:troff+trsz]
print("\n.text VA=0x%X .. 0x%X (file 0x%X)" % (tva, tva+trsz, troff))

LO, HI = BASE + 0x6CC900, BASE + 0x6CD200

# push imm32
print("\n=== .text 中 push imm32 指向服务名串区 ===")
n = 0
for i in range(len(tdata) - 5):
    if tdata[i] == 0x68:
        v = struct.unpack_from("<I", tdata, i + 1)[0]
        if LO <= v <= HI:
            off = v - BASE
            e = data.find(b"\x00", off)
            s = data[off:e].decode("latin1")
            print("  file 0x%06X (VA 0x%08X) push 0x%08X -> %r" % (troff+i, tva+i, v, s))
            n += 1
print("  共 %d" % n)

# mov reg, imm32
print("\n=== .text 中 mov reg,imm32 指向服务名串区 ===")
n = 0
for i in range(len(tdata) - 5):
    if 0xB8 <= tdata[i] <= 0xBF:
        v = struct.unpack_from("<I", tdata, i + 1)[0]
        if LO <= v <= HI:
            off = v - BASE
            e = data.find(b"\x00", off)
            s = data[off:e].decode("latin1")
            print("  file 0x%06X (VA 0x%08X) mov 0x%08X -> %r" % (troff+i, tva+i, v, s))
            n += 1
print("  共 %d" % n)

# cmp r32, imm32 (81 /7) 与 cmp r/m8, imm8 (80 /7), 找 102
print("\n=== .text 中 cmp 立即数 == 102(0x66) 的候选 (81 F8..FF / 83 F8) ===")
cnt = 0
for i in range(len(tdata) - 7):
    b = tdata[i]
    m = tdata[i+1]
    # 81 /7 ib/id  -> modrm reg=7 : 0xF8..0xFF
    if b == 0x81 and (m & 0xF8) == 0xF8:
        v = struct.unpack_from("<I", tdata, i + 2)[0]
        if v == 102:
            print("  cmp r32,102 @file 0x%06X VA 0x%08X" % (troff+i, tva+i))
            cnt += 1
    if b == 0x83 and (m & 0xF8) == 0xF8:
        v = tdata[i+2]
        if v == 102:
            print("  cmp r32,102(short) @file 0x%06X VA 0x%08X" % (troff+i, tva+i))
            cnt += 1
print("  共 %d" % cnt)
