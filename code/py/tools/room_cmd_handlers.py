#!/usr/bin/env python3
"""扫描命令注册序列：mov esi, <cmd_name_va> / call 0x4f37a0
随后 mov [X+4], handler —— 提取 (命令名, handler)。"""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000


def main():
    b = open(DUMP, "rb").read()

    def str_at(va):
        o = va - BASE
        if not (0 <= o < len(b)):
            return None
        z = b.find(b"\x00", o)
        s = b[o:z]
        if s and all(32 <= c < 127 for c in s) and len(s) < 64:
            return s.decode("ascii")
        return None

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    code = b[0x600000:BASE * 0 + 0x700000] if False else b[0x620000:0x6a0000]
    start_va = BASE + 0x620000
    last_name = None
    results = []
    for ins in md.disasm(code, start_va):
        if ins.id == 0:
            continue
        try:
            ops = ins.operands
        except Exception:
            continue
        if ins.mnemonic == "mov" and ops and ops[0].type == 1:
            if ins.reg_name(ops[0].reg) == "esi" and ops[1].type == 2:
                s = str_at(ops[1].imm)
                if s and ("room." in s or "party." in s):
                    last_name = s
        elif ins.mnemonic == "mov" and len(ops) == 2 and ops[0].type == 3:
            if ops[1].type == 2 and last_name:
                # mov dword ptr [reg+disp], imm32
                d = ops[0].mem.disp
                if ops[1].imm > 0x400000:
                    results.append((last_name, ops[1].imm, ins.address))
                    last_name = None

    print("命令 -> handler：")
    seen = set()
    for name, h, at in results:
        if name in seen:
            continue
        seen.add(name)
        print("  %-22s handler=%#010x   (reg@%#x)" % (name, h, at))


if __name__ == "__main__":
    main()
