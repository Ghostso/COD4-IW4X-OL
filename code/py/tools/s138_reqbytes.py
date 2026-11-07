#!/usr/bin/env python3
"""s138_reqbytes: 搜 6/5 请求的 13 字节模板, 以及 0x14+0x08 tag 对的构造点."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000

print("=== 精确 13B 模板 ===")
for pat in [bytes.fromhex("08000000" "00081400" "00000101" "00"),
            bytes.fromhex("0800000000081400000001")]:
    i = 0; hits = []
    while True:
        j = d.find(pat, i)
        if j < 0: break
        hits.append(j); i = j + 1
    print("  %s -> %s" % (pat.hex(), ["0x%X" % (h + VA) for h in hits[:10]]))

print("\n=== 请求构造: push 8 (tag) 之后紧跟 push 0 / push 0x14 的写函数 ===")
# writers use pattern: push tag; lea buf; push; call write
# Look for sequences "6a 08 ... 6a 00" and "6a 08 ... 6a 14"
for tag in (8,):
    pass

# Search for functions that call 0xB75F30 with 8 and then write u32 0 or 20
# Simpler: find 'push 20' near 'push 8' within 20 bytes
for i in range(N - 8):
    if d[i:i+2] == b"\x6a\x08":
        seg = d[i:i+28]
        if b"\x6a\x14" in seg or (b"\x6a\x00" in seg and b"\xb8\x14" in d[i:i+40]):
            print("  0x%08X ctx=%s" % (VA + i, seg.hex()))
