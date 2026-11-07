#!/usr/bin/env python3
"""135 卷工具 I: 重验 as_regfns_v2.json 的 828 个"注册器".

真注册器(逐字节模板, 133 卷 §二):
   ... mov [eax],<自身 vtable> ...  (vtable ∈ 829)
   ... push <短名字符串 imm32> ...
   ... call [edx+0x14]              (寄存器间接, 不是 E8)
函数体长约 0xB9, 以 c2 04 00 / c3 结束.

本工具: 从入口反汇编到第一条 c3 / c2 xx xx; 在**函数自身体内**找
  1) 是否写了 829 的 vtable
  2) 是否有 push <指向 ASCII 短名> 的 imm32
两个都无 -> 不是注册器(假条目).
"""
import json
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\tools"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    if 2 <= len(s) and all(32 <= c < 127 for c in s):
        return s.decode("latin1")
    return None


def analyze(entry):
    code = d[entry - VA:entry - VA + 0x300]
    vt = None
    name = None
    end = len(code)
    for ins in md.disasm(code, entry):
        if ins.mnemonic in ("ret", "retn") or ins.mnemonic == "ret":
            end = ins.address - entry
            break
        if ins.mnemonic.startswith("ret"):
            end = ins.address - entry
            break
        if ins.mnemonic == "mov" and len(ins.operands) == 2:
            a, b = ins.operands
            if a.type == 3 and b.type == 2:   # mem, imm
                try:
                    v = b.imm & 0xFFFFFFFF
                except Exception:
                    v = None
                if v and VA <= v < VA + N:
                    nm = cstr(v)
                    if nm and nm[0].isalpha() and len(nm) >= 3:
                        name = nm
        if ins.mnemonic == "push" and ins.operands and ins.operands[0].type == 2:
            v = ins.operands[0].imm & 0xFFFFFFFF
            if VA <= v < VA + N:
                nm = cstr(v)
                if nm and (nm[0].isalpha() or nm[0] in "_$") and len(nm) >= 3:
                    name = nm
    return name, end


if __name__ == "__main__":
    regs = json.load(open(OUT + r"\as_regfns_v2.json"))
    fakes = []
    for r in regs:
        nm, ln = analyze(r)
        if nm is None:
            fakes.append((r, ln))
    print("总数 %d; 体内找不到'短名 push'的: %d" % (len(regs), len(fakes)))
    for r, ln in fakes:
        print("   0x%08X  (首 ret 在 +0x%X)" % (r, ln))
