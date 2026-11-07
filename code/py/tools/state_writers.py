#!/usr/bin/env python3
"""找 [0x849ba30] 的所有写入点（各种寻址形态）。"""
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
TARGETS = [0x0849ba30, 0x0849ba3d, 0x0849ba50]


def main():
    b = open(DUMP, "rb").read()
    for T in TARGETS:
        pat = struct.pack("<I", T)
        print("=" * 60)
        print("target %#x" % T)
        w = 0
        forms = []
        # mov [T], eax  = A3
        # mov [T], imm32 = C7 05 <T> <imm>
        for i in range(len(b) - 10):
            if b[i] == 0xC7 and b[i + 1] == 0x05 and b[i + 2:i + 6] == pat:
                imm = struct.unpack_from("<I", b, i + 6)[0]
                forms.append(("mov dword imm=%#x" % imm, BASE + i))
                w += 1
            elif b[i] == 0xA3 and b[i + 1:i + 5] == pat:
                forms.append(("mov dword,eax", BASE + i))
                w += 1
        for op, reg in ((b"\x89\x0d", "ecx"), (b"\x89\x15", "edx"),
                        (b"\x89\x1d", "ebx"), (b"\x89\x35", "esi"),
                        (b"\x89\x3d", "edi")):
            for i in range(len(b) - 6):
                if b[i:i + 2] == op and b[i + 2:i + 6] == pat:
                    forms.append(("mov dword,%s" % reg, BASE + i))
                    w += 1
        # 读点统计
        r = 0
        for i in range(len(b) - 5):
            if b[i] in (0xA1,) and b[i + 1:i + 5] == pat:
                r += 1
            elif b[i:i + 2] in (b"\x8b\x0d", b"\x8b\x15", b"\x8b\x1d",
                                b"\x8b\x35", b"\x8b\x3d") and b[i + 2:i + 6] == pat:
                r += 1
            elif b[i:i + 2] == b"\x39\x05" and b[i + 2:i + 6] == pat:
                r += 1
            elif b[i:i + 2] == b"\x83\x3d" and b[i + 2:i + 6] == pat:
                r += 1
        print("  写点 %d，读/比点 %d" % (w, r))
        for name, va in forms:
            print("    %-22s VA %#010x" % (name, va))


if __name__ == "__main__":
    main()
