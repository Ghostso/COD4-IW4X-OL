# -*- coding: utf-8 -*-
"""P0 (精确版): 找 'mov r32, [r32+0x140/0x13C]' 后紧跟 'call 同一寄存器' 的虚调用。

关键：必须**寄存器同源**。仅凭 disp=0x140 会命中大量无关结构体。
做法：反汇编整个可执行区间（线性扫描，遇到明显非法指令就跳过 1 字节重同步），
只保留形如:
    mov  edx, dword ptr [eax + 0x140]
    call edx
的配对。
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
img = open(IMG, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TARGET_DISP = (0x140, 0x13C)
SCAN_LO = 0x401000
SCAN_HI = 0x400000 + len(img)


def main():
    # 先用字节模式定位所有 'mov r32, [r32/r64+disp32]' (8B 80+ / 8B 88..BF)
    cands = []
    for disp in TARGET_DISP:
        pat = struct.pack("<I", disp)
        s = 0
        while True:
            i = img.find(pat, s)
            if i < 0:
                break
            va = 0x400000 + i
            # 取前面 2 字节，检查是否 8B modrm(df)
            if i >= 2:
                b1, b0 = img[i - 2], img[i - 1]
                # 8B 80+reg: mov r32, [r32+disp32]  (modrm mod=10 rm!=100)
                if b1 == 0x8B and 0x80 <= b0 <= 0xBF and (b0 & 7) != 4:
                    cands.append((va - 2, disp, b0))
            s = i + 1
    print("候选 'mov reg,[reg+0x140/0x13C]' 指令 %d 条" % len(cands))
    print()
    hits = []
    for va, disp, modrm in cands:
        code = img[va - 0x400000: va - 0x400000 + 0x20]
        ins_list = list(md.disasm(code, va))
        if len(ins_list) < 2:
            continue
        first = ins_list[0]
        # 取目标寄存器
        dst = None
        if first.operands and first.operands[0].type == 1:
            dst = first.reg_name(first.operands[0].reg)
        if not dst:
            continue
        for nxt in ins_list[1:4]:
            if nxt.mnemonic == "call" and dst in nxt.op_str:
                hits.append((va, disp, first.op_str, nxt.address, nxt.op_str))
                break
    print("=" * 78)
    print("寄存器同源的虚调用（mov reg,[obj+disp] ; call reg）")
    print("=" * 78)
    for va, disp, movs, cva, cs_ in hits:
        tag = {0x140: "accepted", 0x13C: "timedout"}[disp]
        print("  [%s] 0x%08X  %-40s -> 0x%08X  %s"
              % (tag, va, movs, cva, cs_))
    print()
    print("共 %d 条" % len(hits))


if __name__ == "__main__":
    main()
