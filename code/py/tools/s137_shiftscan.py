#!/usr/bin/env python3
"""s137: scan image for shift-by-10/11 and *0x400 (1024) ops."""
import sys
IMG = r"E:\codol_re\client_image_20261027.bin"

def main():
    with open(IMG, "rb") as f:
        data = f.read()
    pats = {
        "shl r32,10 (c1 e0..e7 0a)": [bytes([0xc1, 0xc0 + i, 0x0a]) for i in range(8)],
        "shr r32,10 (c1 e8..ef 0a)": [bytes([0xc1, 0xc0 + 8 + i, 0x0a]) for i in range(8)],
        "shl r64,10 (48 c1 e0..e7 0a)": [bytes([0x48, 0xc1, 0xc0 + i, 0x0a]) for i in range(8)],
        "shr r64,10 (48 c1 e8..ef 0a)": [bytes([0x48, 0xc1, 0xc0 + 8 + i, 0x0a]) for i in range(8)],
        "shl r32,11 (c1 e0..e7 0b)": [bytes([0xc1, 0xc0 + i, 0x0b]) for i in range(8)],
        "shr r32,11 (c1 e8..ef 0b)": [bytes([0xc1, 0xc0 + 8 + i, 0x0b]) for i in range(8)],
        "imul r32,r32,0x400": [bytes([0x69]) + bytes([0xc0 + i * 8 + i]) for i in range(0)],  # todo
    }
    # custom: imul eax, eax, 0x400 = 69 c0 00 04 00 00 ; imul r32,r/m32,imm32 = 69 /r
    imul400 = []
    for rm in range(8):
        for reg in range(8):
            modrm = 0xc0 | (reg << 3) | rm
            imul400.append(bytes([0x69, modrm, 0x00, 0x04, 0x00, 0x00]))
    groups = list(pats.items()) + [("imul r32,r32,0x400", imul400)]
    for name, plist in groups:
        hits = []
        for p in plist:
            i = 0
            while True:
                j = data.find(p, i)
                if j < 0: break
                hits.append((j, p))
                i = j + 1
        print("%-40s : %d hits" % (name, len(hits)))
        for h, p in hits[:12]:
            print("    fileoff=0x%08X VA=0x%08X  %s" % (h, h + 0x400000, p.hex()))

if __name__ == "__main__":
    main()
