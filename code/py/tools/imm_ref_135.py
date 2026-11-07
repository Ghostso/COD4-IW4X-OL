#!/usr/bin/env python3
"""135 卷工具 E: 找一个 imm32(=VA) 在代码里的引用点, 并打印前 4 字节来分类指令. """
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

OP = {
    0x68: "push imm32",
    0xB8: "mov eax,imm32",
    0xB9: "mov ecx,imm32",
    0xBA: "mov edx,imm32",
    0xBB: "mov ebx,imm32",
    0xBE: "mov esi,imm32",
    0xBF: "mov edi,imm32",
    0xC7: "mov r/m32,imm32",
    0xA1: "mov eax,[abs]",
    0xA3: "mov [abs],eax",
}

if __name__ == "__main__":
    for a in sys.argv[1:]:
        tgt = int(a, 0)
        pat = struct.pack("<I", tgt)
        pos = 0
        out = []
        while True:
            i = d.find(pat, pos)
            if i < 0:
                break
            pos = i + 1
            # 该 imm32 的起始字节 = i; 判断前 1~2 字节是否指令操作码
            lab = "?"
            for back in (1, 2):
                if i - back >= 0:
                    op = d[i - back]
                    if op in OP and back == 1:
                        lab = OP[op]
                        break
            out.append((VA + i, lab, " ".join("%02x" % c for c in d[i - 3:i + 6])))
        print("imm32 0x%08X : %d 处" % (tgt, len(out)))
        for va, lab, ctx in out:
            print("   0x%08X  %-16s  ctx: %s" % (va, lab, ctx))
        print()
